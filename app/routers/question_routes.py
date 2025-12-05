


from fastapi import APIRouter, HTTPException, Depends
from app.security import verify_api_key
from app.database import get_db
from app.services.question_service import (
    generate_consequential_questions,
    generate_followup_question
)
from app.services.evaluation_service import evaluate_answer

router = APIRouter(prefix="/questions", tags=["Questions"])

TOTAL_QUESTIONS = 15
CONSEQUENTIAL_MAX = 8
FOLLOWUP_MAX = 7


def get_question_counts(interview_id: int):
    """Count total questions asked and split by type."""
    with get_db() as db:
        total_asked = db.execute("""
            SELECT COUNT(*) AS cnt FROM questions
            WHERE interview_id = ? AND asked = 1
        """, (interview_id,)).fetchone()["cnt"]

        conseq_asked = db.execute("""
            SELECT COUNT(*) AS cnt FROM questions
            WHERE interview_id = ? AND asked = 1 AND source_type='consequential'
        """, (interview_id,)).fetchone()["cnt"]

        follow_asked = db.execute("""
            SELECT COUNT(*) AS cnt FROM questions
            WHERE interview_id = ? AND asked = 1 AND source_type='followup'
        """, (interview_id,)).fetchone()["cnt"]

    return total_asked, conseq_asked, follow_asked


def fetch_next_consequential(interview_id: int) -> str:
    """Pull the next unasked consequential question."""
    with get_db() as db:
        row = db.execute("""
            SELECT id, question_text FROM questions
            WHERE interview_id = ? AND asked = 0 AND source_type='consequential'
            ORDER BY id ASC LIMIT 1
        """, (interview_id,)).fetchone()

    if not row:
        raise ValueError("No more consequential questions available.")

    # Mark asked
    with get_db



@router.post("/{question_id}/answer")
def submit_answer(question_id: int, answer: str, user=Depends(verify_api_key)):
    """
    Handles evaluation workflow:
    - Evaluate answer strictly
    - Retry if vague (1 max)
    - Attach next question if interview not done
    - Mark completion status when last Q done
    """
    with get_db() as db:
        row = db.execute("""
            SELECT q.interview_id, q.question_text
            FROM questions q
            WHERE q.id=?
        """, (question_id,)).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Question not found")

    interview_id = row["interview_id"]
    question_text = row["question_text"]

    # Evaluate the answer using the AI model
    result = evaluate_answer(question_text, answer, interview_id, question_id)

    # Retry needed (no next question provided)
    if result.get("retry_required", False):
        return {
            "message": "Answer too vague. Retry required.",
            "retry_required": True,
            "feedback": result.get("reject_reason", "")
        }

    # Mark interview state as in-progress on first answer
    with get_db() as db:
        db.execute(
            "UPDATE interviews SET status='IN_PROGRESS' WHERE id=? AND status='GENERATING_QUESTIONS'",
            (interview_id,)
        )

    # Count answered questions
    with get_db() as db:
        answered = db.execute("""
            SELECT COUNT(*) AS cnt FROM answers WHERE score IS NOT NULL
        """).fetchone()["cnt"]

    # If this was the final question
    if answered >= TOTAL_QUESTIONS:
        with get_db() as db:
            db.execute(
                "UPDATE interviews SET status='COMPLETED' WHERE id=?",
                (interview_id,)
            )
        return {
            "message": "Interview completed. Fetch final report.",
            "done": True
        }

    # Otherwise fetch the next question automatically
    with get_db() as db:
        # Mark asked questions to get next
        conseq_count = db.execute("""
            SELECT COUNT(*) AS cnt FROM questions
            WHERE interview_id=? AND asked=1 AND source_type='consequential'
        """, (interview_id,)).fetchone()["cnt"]

        follow_count = db.execute("""
            SELECT COUNT(*) AS cnt FROM questions
            WHERE interview_id=? AND asked=1 AND source_type='followup'
        """, (interview_id,)).fetchone()["cnt"]

    # Determine next question type
    if follow_count < answered and follow_count < FOLLOWUP_MAX:
        next_q = generate_followup_question(interview_id)
    else:
        # Use unasked consequential
        with get_db() as db:
            row = db.execute("""
                SELECT id, question_text FROM questions
                WHERE interview_id=? AND asked=0 AND source_type='consequential'
                ORDER BY id ASC LIMIT 1
            """, (interview_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=500, detail="Missing pre-generated consequential questions")
            q_id = row["id"]
            next_q = row["question_text"]
            db.execute("UPDATE questions SET asked=1 WHERE id=?", (q_id,))

    return {
        "message": "Answer evaluated",
        "retry_required": False,
        "score": result.get("score"),
        "feedback": result.get("feedback"),
        "next_question": next_q
    }

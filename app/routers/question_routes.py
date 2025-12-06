from fastapi import APIRouter, HTTPException, Depends
from app.utils.security import verify_api_key
from app.database import get_db
from app.services.question_service import (
    generate_consequential_questions,
    generate_followup_question
)
from app.services.evaluation_service import evaluate_answer
from app.config import get_question_limits

router = APIRouter(prefix="/questions", tags=["Questions"])

#TOTAL_QUESTIONS, CONSEQUENTIAL_MAX, FOLLOWUP_MAX = get_question_limits() # Removed global constants


from pydantic import BaseModel

class AnswerInput(BaseModel):
    answer: str


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


def fetch_next_consequential(interview_id: int) -> tuple[int, str]:
    """Pull and mark the next unasked consequential question."""
    with get_db() as db:
        row = db.execute("""
            SELECT id, question_text
            FROM questions
            WHERE interview_id = ?
              AND asked = 0
              AND source_type = 'consequential'
            ORDER BY id ASC
            LIMIT 1
        """, (interview_id,)).fetchone()

    if not row:
        raise ValueError("No more consequential questions available.")

    q_id = row["id"]
    question_text = row["question_text"]

    # Mark as asked
    with get_db() as db:
        db.execute(
            "UPDATE questions SET asked = 1 WHERE id = ?",
            (q_id,)
        )

    return q_id, question_text


@router.post("/{question_id}/answer")
def submit_answer(
    question_id: int,
    data: AnswerInput,  # receives JSON body: {"answer": "..."}
    user=Depends(verify_api_key)
):
    answer = data.answer.strip()
    if not answer:
        raise HTTPException(status_code=400, detail="Answer cannot be empty")

    # Lookup question & interview context
    with get_db() as db:
        row = db.execute("""
            SELECT q.interview_id, q.question_text
            FROM questions q
            WHERE q.id = ?
        """, (question_id,)).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Question not found")

    interview_id = row["interview_id"]
    question_text = row["question_text"]

    # Evaluate
    result = evaluate_answer(
        question_text,
        answer,
        interview_id,
        question_id
    )

    # Retry mechanism
    if result.get("retry_required", False):
        return {
            "message": "Answer too vague. Retry required.",
            "retry_required": True,
            "feedback": result.get("reject_reason", "")
        }

    # Update interview state on first valid answer
    with get_db() as db:
        db.execute(
            "UPDATE interviews SET status='IN_PROGRESS' "
            "WHERE id=? AND status='GENERATING_QUESTIONS'",
            (interview_id,)
        )

    # Count how many answers scored for this interview
    with get_db() as db:
        answered = db.execute("""
            SELECT COUNT(*) AS cnt
            FROM answers
            WHERE score IS NOT NULL
              AND question_id IN (SELECT id FROM questions WHERE interview_id=?)
        """, (interview_id,)).fetchone()["cnt"]

    # Get dynamic limits
    TOTAL_QUESTIONS, _, FOLLOWUP_MAX = get_question_limits()

    # End of interview?
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

    # Counts for next question logic
    with get_db() as db:
        conseq_count = db.execute("""
            SELECT COUNT(*) AS cnt
            FROM questions
            WHERE interview_id=? AND asked=1 AND source_type='consequential'
        """, (interview_id,)).fetchone()["cnt"]

        follow_count = db.execute("""
            SELECT COUNT(*) AS cnt
            FROM questions
            WHERE interview_id=? AND asked=1 AND source_type='followup'
        """, (interview_id,)).fetchone()["cnt"]

    # Pick next Q
    if follow_count < answered and follow_count < FOLLOWUP_MAX:
        next_q = generate_followup_question(interview_id)
        q_id = None  # Not stored here; service handles marking
    else:
        # Ensure supply before fetching
        generate_consequential_questions(interview_id)
        q_id, next_q = fetch_next_consequential(interview_id)

    return {
        "message": "Answer evaluated",
        "retry_required": False,
        "score": result.get("score"),
        "feedback": result.get("feedback"),
        "next_question": next_q,
        "next_question_id": q_id
    }


@router.get("/config")
def get_public_question_config(user=Depends(verify_api_key)):
    """Return the configured number of questions (for frontend progress bar)."""
    total, conseq, follow = get_question_limits()
    return {
        "total_questions": total,
        "consequential_max": conseq,
        "followup_max": follow
    }


@router.get("/next/{interview_id}")
def get_next_question(interview_id: int, user=Depends(verify_api_key)):
    """Fetch the next unasked question. Generate if needed."""

    with get_db() as db:
        # Count asked questions
        answered = db.execute("""
            SELECT COUNT(*) AS cnt FROM answers
            WHERE question_id IN (
                SELECT id FROM questions WHERE interview_id=?
            ) AND score IS NOT NULL
        """, (interview_id,)).fetchone()["cnt"]

        # Get dynamic limits
        TOTAL_QUESTIONS, CONSEQUENTIAL_MAX, _ = get_question_limits()

        # Is interview complete?
        if answered >= TOTAL_QUESTIONS:
            return {"done": True, "message": "Interview already completed"}

        # Count consequential asked
        conseq_asked = db.execute("""
            SELECT COUNT(*) AS cnt FROM questions
            WHERE interview_id=? AND asked=1 AND source_type='consequential'
        """, (interview_id,)).fetchone()["cnt"]

    # Pre-generate consequential if needed
    if conseq_asked < CONSEQUENTIAL_MAX:
        generate_consequential_questions(interview_id)

    # Fetch next unasked question
    with get_db() as db:
        row = db.execute("""
            SELECT id, question_text, source_type
            FROM questions
            WHERE interview_id=? AND asked=0
            ORDER BY id ASC LIMIT 1
        """, (interview_id,)).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="No more questions available")

        q_id = row["id"]
        q_text = row["question_text"]

        # Mark question asked
        db.execute("UPDATE questions SET asked=1 WHERE id=?", (q_id,))

    return {
        "question_id": q_id,
        "question": q_text,
        "done": False
    }

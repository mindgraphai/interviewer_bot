from fastapi import APIRouter, Depends, HTTPException
from app.utils.security import verify_api_key
from app.database import get_db
import json

router = APIRouter(prefix="/report", tags=["Report"])


@router.get("/{interview_id}")
def get_final_report(interview_id: int, user=Depends(verify_api_key)):

    # Pull state and profile
    with get_db() as db:
        interview = db.execute("""
            SELECT status, candidate_profile
            FROM interviews WHERE id=?
        """, (interview_id,)).fetchone()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if interview["status"] != "COMPLETED":
        raise HTTPException(status_code=400, detail="Interview not completed yet")

    candidate_profile = json.loads(interview["candidate_profile"])

    # Aggregate score from answers
    with get_db() as db:
        avg_score = db.execute("""
            SELECT AVG(score) AS score
            FROM answers
            WHERE question_id IN (
                SELECT id FROM questions WHERE interview_id=?
            )
              AND score IS NOT NULL
        """, (interview_id,)).fetchone()["score"]

    avg_score = avg_score or 0

    # Load pass threshold
    with get_db() as db:
        row = db.execute("SELECT value FROM pass_threshold LIMIT 1").fetchone()

    threshold = row["value"] if row else 0.5  # default 50%

    passed = avg_score >= threshold * 5  # score max is 5

    return {
        "interview_id": interview_id,
        "candidate_profile": candidate_profile,
        "average_score": round(avg_score, 2),
        "passed": passed,
        "threshold": threshold
    }

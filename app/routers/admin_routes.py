from fastapi import APIRouter, HTTPException, Depends
from app.database import get_db
from app.security import verify_api_key

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/set_job_description")
def set_job_description(content: str, user=Depends(verify_api_key)):
    # Only allow admin user (username: admin)
    if user["username"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin can update JD")

    with get_db() as db:
        db.execute("DELETE FROM job_description")  # keep only 1 global JD
        db.execute(
            "INSERT INTO job_description (content) VALUES (?)",
            (content,)
        )

    return {"message": "Job description updated successfully"}

from pydantic import BaseModel

class ThresholdUpdate(BaseModel):
    value: float  # 0.0 - 1.0


@router.post("/set_threshold")
def set_threshold(data: ThresholdUpdate, user=Depends(verify_api_key)):
    if user["username"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    val = data.value
    if not (0 <= val <= 1):
        raise HTTPException(status_code=400, detail="Threshold must be 0-1")

    with get_db() as db:
        db.execute("DELETE FROM pass_threshold")
        db.execute("INSERT INTO pass_threshold (value) VALUES (?)", (val,))

    return {"message": f"Hiring threshold set to {val * 100:.1f}%"}

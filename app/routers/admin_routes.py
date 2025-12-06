from fastapi import APIRouter, HTTPException, Depends
from app.database import get_db
from app.utils.security import verify_api_key

router = APIRouter(prefix="/admin", tags=["Admin"])


from fastapi import UploadFile, File
from app.utils.pdf2text import extract_text_from_pdf

@router.post("/set_job_description")
async def set_job_description(
    file: UploadFile = File(...),
    user=Depends(verify_api_key)
):
    if user["username"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin can update JD")

    # Read and extract text from PDF
    pdf_bytes = await file.read()
    jd_text = extract_text_from_pdf(pdf_bytes)

    if not jd_text or len(jd_text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Invalid or unreadable JD PDF")

    # Store JD as plaintext only
    with get_db() as db:
        db.execute("DELETE FROM job_description")
        db.execute(
            "INSERT INTO job_description (content) VALUES (?)",
            (jd_text,)
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

class QuestionConfigUpdate(BaseModel):
    total_questions: int
    consequential_max: int
    followup_max: int

@router.post("/set_question_config")
def set_question_config(cfg: QuestionConfigUpdate, user=Depends(verify_api_key)):
    if user["username"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    with get_db() as db:
        db.execute("DELETE FROM question_config")
        db.execute(
            "INSERT INTO question_config (total_questions, consequential_max, followup_max) VALUES (?, ?, ?)",
            (cfg.total_questions, cfg.consequential_max, cfg.followup_max)
        )

    return {"message": "Question config updated successfully", "config": cfg}

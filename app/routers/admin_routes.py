from fastapi import APIRouter, HTTPException, Depends
from app.database import get_db
from app.utils.security import verify_api_key
from pydantic import BaseModel

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


class JDContent(BaseModel):
    content: str


@router.post("/set_job_description_content")
def set_job_description_content(
    data: JDContent,
    user=Depends(verify_api_key)
):
    if user["username"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin can update JD")

    if not data.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    with get_db() as db:
        db.execute("DELETE FROM job_description")
        db.execute(
            "INSERT INTO job_description (content) VALUES (?)",
            (data.content,)
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


@router.get("/get_question_config")
def get_question_config(user=Depends(verify_api_key)):
    if user["username"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
        
    with get_db() as db:
        row = db.execute("SELECT * FROM question_config LIMIT 1").fetchone()
        
    if not row:
         return {
            "total_questions": 5,
            "consequential_max": 3,
            "followup_max": 2
        }
        
    return {
        "total_questions": row["total_questions"],
        "consequential_max": row["consequential_max"],
        "followup_max": row["followup_max"]
    }


@router.get("/candidates")
def list_candidates(user=Depends(verify_api_key)):
    if user["username"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    # Fetch candidates with some aggregated stats
    # Fetch candidates with some aggregated stats
    with get_db() as db:
        # Get all users (except admin), joined with their interviews (if any)
        # If multiple interviews, this returns multiple rows per user (which is fine, distinct candidacies)
        # If no interview, returns one row with null interview fields
        rows = db.execute("""
            SELECT 
                u.id as user_id,
                u.username as name,
                i.id as interview_id,
                i.status,
                i.created_at,
                (
                    SELECT AVG(a.score) 
                    FROM answers a 
                    JOIN questions q ON a.question_id = q.id 
                    WHERE q.interview_id = i.id AND a.score IS NOT NULL
                ) as avg_score
            FROM users u
            LEFT JOIN interviews i ON i.id = (
                SELECT id FROM interviews 
                WHERE user_id = u.id 
                ORDER BY created_at DESC 
                LIMIT 1
            )
            WHERE u.username != 'admin'
            ORDER BY i.created_at DESC
        """).fetchall()
        
        candidates = []
        for r in rows:
            score = r["avg_score"] if r["avg_score"] else 0.0
            status = r["status"] if r["status"] else "NO_INTERVIEW"
            interview_id = r["interview_id"] # Matches SQL alias

            candidates.append({
                "id": interview_id, # Can be None
                "user_id": r["user_id"],
                "name": r["name"],
                "score": round(score, 1),
                "domain": "General", 
                "status": status
            })
            
    return candidates

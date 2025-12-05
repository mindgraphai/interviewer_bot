from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.security import verify_api_key
from app.services.resume_service import process_resume_upload

router = APIRouter(prefix="/interviews", tags=["Interview"])


@router.post("/upload_resume")
async def upload_resume(
    file: UploadFile = File(...),
    user=Depends(verify_api_key)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF resumes allowed")

    file_bytes = await file.read()
    try:
        interview_id, resume_text = process_resume_upload(user["user_id"], file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": "Resume uploaded and processed successfully",
        "interview_id": interview_id
    }

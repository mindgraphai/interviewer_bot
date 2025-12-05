from fastapi import APIRouter, Depends, HTTPException
from app.security import verify_api_key
from app.services.report_service import generate_final_report
from app.models.report_models import FinalReport

router = APIRouter(prefix="/report", tags=["Report"])


@router.get("/{interview_id}", response_model=FinalReport)
def get_final_report(interview_id: int, user=Depends(verify_api_key)):
    try:
        return generate_final_report(interview_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

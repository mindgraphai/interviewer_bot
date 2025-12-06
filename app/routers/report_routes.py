from fastapi import APIRouter, Depends, HTTPException
from app.utils.security import verify_api_key
from app.services.report_service import generate_final_report
from app.database import get_db
import json

router = APIRouter(prefix="/report", tags=["Report"])


@router.get("/{interview_id}")
def get_final_report(interview_id: int, user=Depends(verify_api_key)):

    # Ensure interview exists and check for stored report
    with get_db() as db:
        row = db.execute(
            "SELECT status, final_report FROM interviews WHERE id=?",
            (interview_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Interview not found")

    # If report already stored, just return it
    if row["final_report"]:
        try:
            return json.loads(row["final_report"])
        except Exception:
            # Fallback: regenerate if stored JSON is somehow corrupt
            report = generate_final_report(interview_id)
            return report.model_dump()

    # If no stored report yet, only allow if interview was completed
    if row["status"] not in ("COMPLETED", "REPORTED"):
        raise HTTPException(
            status_code=400,
            detail=f"Interview not ready for reporting. Current state: {row['status']}",
        )

    # Generate, save (inside service), and return
    report = generate_final_report(interview_id)
    return report.model_dump()

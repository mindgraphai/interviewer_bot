from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.database import get_db
from app.services.question_service import generate_consequential_questions, generate_followup_question
from app.services.evaluation_service import evaluate_answer
from app.services.report_service import generate_final_report
from app.config import get_question_limits
import json

router = APIRouter(prefix="/interview", tags=["Candidate"])

async def verify_interview_token(token: str):
    with get_db() as db:
        row = db.execute("SELECT * FROM interviews WHERE access_token = ?", (token,)).fetchone()
    
    if not row:
         raise HTTPException(status_code=404, detail="Invalid token")
    
    return row

def get_next_question_logic(interview_id: int):    
    with get_db() as db:
        # Check if interview is done
        answered_count = db.execute("""
            SELECT COUNT(*) AS cnt FROM answers
            WHERE question_id IN (SELECT id FROM questions WHERE interview_id=?)
            AND score IS NOT NULL
        """, (interview_id,)).fetchone()["cnt"]
        
        TOTAL, CONSEQUENTIAL, FOLLOWUP = get_question_limits()
        
        if answered_count >= TOTAL:
             return {"message": "Interview completed", "done": True}

        # Check existing questions count
        total_questions_db = db.execute("SELECT COUNT(*) as cnt FROM questions WHERE interview_id=?", (interview_id,)).fetchone()["cnt"]
        
    if total_questions_db == 0:
        generate_consequential_questions(interview_id)
        
    # Get next unasked
    with get_db() as db:
        row = db.execute("""
            SELECT id, question_text, source_type
            FROM questions
            WHERE interview_id=? AND asked=0
            ORDER BY id ASC LIMIT 1
        """, (interview_id,)).fetchone()
        
        if not row:
             # Try refreshing consequential if none left
             with get_db() as db:
                  conseq_count = db.execute("SELECT COUNT(*) as cnt FROM questions WHERE interview_id=? AND source_type='consequential'", (interview_id,)).fetchone()["cnt"]
             
             if conseq_count < CONSEQUENTIAL:
                  generate_consequential_questions(interview_id)
                  with get_db() as db:
                      row = db.execute("""
                          SELECT id, question_text
                          FROM questions
                          WHERE interview_id=? AND asked=0
                          ORDER BY id ASC LIMIT 1
                      """, (interview_id,)).fetchone()
        
        if not row:
             return {"message": "No more questions currently. Submit last answer to proceed.", "done": False}

        q_id = row["id"]
        q_text = row["question_text"]
        
        # Mark asked
        db.execute("UPDATE questions SET asked=1 WHERE id=?", (q_id,))
        
    return {
        "question_id": q_id,
        "question": q_text,
        "done": False
    }

@router.get("/start/{token}")
async def start_interview(token: str, interview=Depends(verify_interview_token)):
    interview_id = interview["id"]
    
    if interview["status"] in ["CREATED", "INVITED"]:
        with get_db() as db:
             db.execute("UPDATE interviews SET status='STARTED' WHERE id=?", (interview_id,))
             
    if interview["status"] in ["COMPLETED", "REPORTED"]:
         return {"message": "Interview completed", "done": True}
         
    TOTAL, _, _ = get_question_limits() 
    result = get_next_question_logic(interview_id)
    result["total_questions"] = TOTAL
    return result
@router.get("/{token}/next")
async def get_next_question(token: str, interview=Depends(verify_interview_token)):
    if interview["status"] in ["COMPLETED", "REPORTED"]:
         return {"message": "Interview completed", "done": True}
    return get_next_question_logic(interview["id"])
    
@router.get("/{token}/report")
async def get_candidate_report(token: str, interview=Depends(verify_interview_token)):
    if interview["status"] not in ["COMPLETED", "REPORTED"]:
         return {"message": "Interview not yet complete", "ready": False}
         
    interview_id = interview["id"]
    
    # Check if report exists
    if interview["final_report"]:
         try:
             return json.loads(interview["final_report"])
         except Exception:
             pass

    # If no report but status implies done, generate it (idempotent service)
    try:
        report = generate_final_report(interview_id)
        return report.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

class AnswerInput(BaseModel):
    answer: str

@router.post("/{token}/answer")
async def submit_answer(token: str, data: AnswerInput, interview=Depends(verify_interview_token)):
    interview_id = interview["id"]
    answer = data.answer.strip()
    
    if not answer:
        raise HTTPException(status_code=400, detail="Answer cannot be empty")

    # Find current question (Latest asked)
    with get_db() as db:
        q_row = db.execute("""
            SELECT id, question_text, source_type 
            FROM questions 
            WHERE interview_id=? AND asked=1
            ORDER BY id DESC LIMIT 1
        """, (interview_id,)).fetchone()
        
    if not q_row:
         raise HTTPException(status_code=400, detail="No active question found")
         
    question_id = q_row["id"]
    question_text = q_row["question_text"]
    
    # Evaluate
    result = evaluate_answer(question_text, answer, interview_id, question_id)
    
    if result.get("retry_required"):
         return {"retry_required": True, "feedback": result.get("reject_reason"), "message": "Answer vague, please retry."}
         
    # Update status to IN_PROGRESS
    if interview["status"] == "STARTED":
         with get_db() as db:
             db.execute("UPDATE interviews SET status='IN_PROGRESS' WHERE id=?", (interview_id,))
             
    # Check if we should terminate or generate followup
    TOTAL, CONSEQUENTIAL, FOLLOWUP_MAX = get_question_limits()
    
    with get_db() as db:
        answered = db.execute("SELECT COUNT(*) as cnt FROM answers WHERE question_id IN (SELECT id FROM questions WHERE interview_id=?) AND score IS NOT NULL", (interview_id,)).fetchone()["cnt"]
        
    if answered >= TOTAL:
        with get_db() as db:
             db.execute("UPDATE interviews SET status='COMPLETED' WHERE id=?", (interview_id,))
        try:
             generate_final_report(interview_id)
        except Exception as e:
             # Log error but don't crash
             print(f"Report generation error: {e}")
        return {"done": True, "message": "Interview completed"}

    # Generate followup if appropriate
    with get_db() as db:
        followup_count = db.execute("SELECT COUNT(*) as cnt FROM questions WHERE interview_id=? AND source_type='followup'", (interview_id,)).fetchone()["cnt"]
    
    if q_row["source_type"] == "consequential" and followup_count < FOLLOWUP_MAX:
         generate_followup_question(interview_id)
         
    return {"done": False, "message": "Answer accepted"}

import json
from openai import OpenAI
from app.config import OPENAI_API_KEY
from app.database import get_db

def get_openai_client():
    return OpenAI(api_key=OPENAI_API_KEY)


def get_profile_and_jd(interview_id: int):
    """Fetch resume-derived profile + JD text."""
    with get_db() as db:
        profile_row = db.execute(
            "SELECT candidate_profile FROM interviews WHERE id=?",
            (interview_id,)
        ).fetchone()

        jd_row = db.execute(
            "SELECT content FROM job_description"
        ).fetchone()

    profile = json.loads(profile_row["candidate_profile"]) if profile_row else {}
    jd = jd_row["content"] if jd_row else ""

    return profile, jd


def evaluate_answer(question: str, answer: str, interview_id: int, question_id: int):
    """
    Evaluate answer quality using strict elite filters.
    Handles:
      - Vagueness detection
      - Hard scoring
      - Per-skill confidence scoring
    """
    profile, jd = get_profile_and_jd(interview_id)

    prompt = f"""
Evaluate the candidate's answer based strictly on elite top-5% interview standards.

Question:
{question}

Candidate Answer:
{answer}

Candidate Profile:
{json.dumps(profile)}

Job Description:
{jd}

Respond with valid JSON ONLY matching this structure:
{{
  "score": <integer 1-5>,
  "is_vague": <true|false>,
  "skill_confidence": {{
    "skill_name_1": <int 1-100>,
    "skill_name_2": <int 1-100>
  }},
  "feedback": "Medium-length constructive explanation",
  "reject_reason": "If vague, explain what lacks. Else empty string."
}}

Rules:
- If vague → score must be 1 and is_vague=true with a clear reject_reason
- Penalize theoretical/cliché/no-tradeoff answers
- Reward specific, correct, practical reasoning
- No markdown allowed
"""

    response = get_openai_client().chat.completions.create(
        model="gpt-4o",
        temperature=0.2,
        messages=[
            {"role": "system", "content": "Return JSON only! No markdown."},
            {"role": "user", "content": prompt}
        ]
    )

    result = json.loads(response.choices[0].message.content)
    _store_evaluation(interview_id, question_id, answer, result)

    return result


def _store_evaluation(interview_id: int, question_id: int, answer: str, result: dict):
    """
    Persist scoring + retry logic + skill confidence.
    """
    score = result.get("score", 1)
    is_vague = result.get("is_vague", False)
    skill_conf = result.get("skill_confidence", {})

    with get_db() as db:
        # Replay last answer row to check retry flag
        prev = db.execute(
            "SELECT retry_used FROM answers WHERE question_id=?",
            (question_id,)
        ).fetchone()

        retry_used = prev["retry_used"] if prev else 0

        # If vague and retry unused → request retry instead of scoring
        if is_vague and retry_used == 0:
            db.execute(
                "UPDATE answers SET answer_text=?, retry_used=1, score=NULL WHERE question_id=?",
                (answer, question_id)
            )
            result["retry_required"] = True
            return

        # Finalize scoring
        db.execute(
            "UPDATE answers SET answer_text=?, score=?, retry_used=? WHERE question_id=?",
            (answer, score, retry_used, question_id)
        )

        # Update skill confidence values in skills table
        # (Insert skills if not yet stored for interview)
        for skill, conf in skill_conf.items():
            # Try update first
            row = db.execute("""
                SELECT id FROM skills
                WHERE interview_id=? AND name=?
            """, (interview_id, skill)).fetchone()

            if row:
                db.execute(
                    "UPDATE skills SET confidence_score=? WHERE id=?",
                    (conf, row["id"])
                )
            else:
                db.execute(
                    "INSERT INTO skills (interview_id, name, importance_score, confidence_score) "
                    "VALUES (?, ?, 50, ?)",
                    (interview_id, skill, conf)
                )

import json
from datetime import datetime
from openai import OpenAI
from app.config import OPENAI_API_KEY
from app.database import get_db
from app.models.report_models import FinalReport, SkillAssessment


def get_openai_client():
    return OpenAI(api_key=OPENAI_API_KEY)


def _get_threshold() -> float:
    """Return stored threshold or default 0.85."""
    with get_db() as db:
        row = db.execute("SELECT value FROM pass_threshold LIMIT 1").fetchone()
    return float(row["value"]) if row else 0.85


def _get_scores(interview_id: int):
    """Fetch only this interview's scores."""
    with get_db() as db:
        rows = db.execute("""
            SELECT score
            FROM answers
            WHERE score IS NOT NULL
              AND question_id IN (
                  SELECT id FROM questions WHERE interview_id = ?
              )
        """, (interview_id,)).fetchall()
    return [r["score"] for r in rows]


def _get_skill_scores(interview_id: int):
    """Return skills with weighting."""
    with get_db() as db:
        rows = db.execute("""
            SELECT name, importance_score, confidence_score
            FROM skills
            WHERE interview_id = ?
        """, (interview_id,)).fetchall()

    return [
        {
            "name": r["name"],
            "importance_score": r["importance_score"],
            "confidence_score": r["confidence_score"],
            "weighted": r["importance_score"] * r["confidence_score"],
        }
        for r in rows
    ]


def _classify_strengths_and_weaknesses(skills: list):
    if not skills:
        return [], []
    sorted_skills = sorted(skills, key=lambda s: s["weighted"], reverse=True)
    return sorted_skills[:3], sorted_skills[-3:]


def _get_ai_commentary(strengths, weaknesses):
    prompt = f"""
Provide structured commentary:

Strengths: {json.dumps(strengths)}
Weaknesses: {json.dumps(weaknesses)}

JSON only:
{{
  "strength_comments": {{ skill_name: commentary }},
  "weakness_comments": {{ skill_name: commentary }},
  "anything_extra": "short remark"
}}
"""
    response = get_openai_client().chat.completions.create(
        model="gpt-4o",
        temperature=0.25,
        messages=[
            {"role": "system", "content": "Return JSON only"},
            {"role": "user", "content": prompt},
        ],
    )
    return json.loads(response.choices[0].message.content)


def generate_final_report(interview_id: int) -> FinalReport:
    """Compute final report, update DB, and return Pydantic model."""
    scores = _get_scores(interview_id)
    threshold = _get_threshold()
    total_score = sum(scores)
    n = len(scores)

    # Scores are 1–5 → normalize to 0–1
    final_percentage = (total_score - n) / (4 * n) if n > 0 else 0.0

    skills_raw = _get_skill_scores(interview_id)
    strengths_raw, weaknesses_raw = _classify_strengths_and_weaknesses(skills_raw)
    ai_comments = _get_ai_commentary(strengths_raw, weaknesses_raw)

    is_selected = final_percentage >= threshold
    recommendation = "SELECTED" if is_selected else "REJECTED"

    strengths = [
        SkillAssessment(
            skill=s["name"],
            confidence_score=s["confidence_score"],
            importance_score=s["importance_score"],
            weighted_score=s["weighted"],
            commentary=ai_comments["strength_comments"].get(s["name"], ""),
        )
        for s in strengths_raw
    ]

    weaknesses = [
        SkillAssessment(
            skill=s["name"],
            confidence_score=s["confidence_score"],
            importance_score=s["importance_score"],
            weighted_score=s["weighted"],
            commentary=ai_comments["weakness_comments"].get(s["name"], ""),
        )
        for s in weaknesses_raw
    ]

    report = FinalReport(
        report_generated_at=datetime.utcnow().isoformat(),
        final_score=total_score,
        final_percentage=round(final_percentage, 3),
        pass_threshold=threshold,
        recommendation=recommendation,
        recommendation_rationale=(
            "Candidate exceeded expectations for the role."
            if is_selected
            else "Candidate did not meet the required skill depth for the role."
        ),
        strengths=strengths,
        weaknesses=weaknesses,
        anything_extra=ai_comments.get("anything_extra", ""),
    )

    # Persist report JSON + status
    with get_db() as db:
        db.execute(
            "UPDATE interviews SET status='REPORTED', final_report=? WHERE id=?",
            (json.dumps(report.model_dump()), interview_id),
        )

    return report

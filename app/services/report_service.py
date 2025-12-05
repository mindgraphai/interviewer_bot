import json
from datetime import datetime
from openai import OpenAI
from app.config import OPENAI_API_KEY
from app.database import get_db
from app.models.report_models import FinalReport, SkillAssessment


client = OpenAI(api_key=OPENAI_API_KEY)


def _get_threshold() -> float:
    """Return stored threshold or default 0.85"""
    with get_db() as db:
        row = db.execute("SELECT value FROM pass_threshold").fetchone()

    return float(row["value"]) if row else 0.85


def _get_scores(interview_id: int):
    """Fetch all evaluated scores from DB"""
    with get_db() as db:
        rows = db.execute("""
            SELECT score FROM answers
            WHERE score IS NOT NULL
        """).fetchall()
    return [r["score"] for r in rows]


def _get_skill_scores(interview_id: int):
    """Return a dict of skill metrics"""
    with get_db() as db:
        rows = db.execute("""
            SELECT name, importance_score, confidence_score
            FROM skills
            WHERE interview_id=?
        """, (interview_id,)).fetchall()

    return [
        {
            "name": r["name"],
            "importance_score": r["importance_score"],
            "confidence_score": r["confidence_score"],
            "weighted": r["importance_score"] * r["confidence_score"]
        }
        for r in rows
    ]


def _classify_strengths_and_weaknesses(skills: list):
    """Split into strengths vs weaknesses"""
    if not skills:
        return [], []

    sorted_skills = sorted(skills, key=lambda s: s["weighted"], reverse=True)

    strengths = sorted_skills[:3]   # top 3
    weaknesses = sorted_skills[-3:] # bottom 3

    return strengths, weaknesses


def _get_ai_commentary(strengths, weaknesses):
    prompt = f"""
Provide a structured evaluation commentary:

Strengths: {json.dumps(strengths)}
Weaknesses: {json.dumps(weaknesses)}

For each skill provide:
- Multi-sentence explanation of concrete strengths or weaknesses
- Avoid clichés and vague fluff
- JSON only with fields:
  {{
    "strength_comments": {{skill_name: commentary}},
    "weakness_comments": {{skill_name: commentary}},
    "anything_extra": "short remark"
  }}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.25,
        messages=[
            {"role": "system", "content": "Return JSON only"},
            {"role": "user", "content": prompt}
        ]
    )
    return json.loads(response.choices[0].message.content)


def generate_final_report(interview_id: int) -> FinalReport:
    scores = _get_scores(interview_id)
    threshold = _get_threshold()
    total_score = sum(scores)
    final_percentage = (total_score - 15) / 60  # normalized 0-1

    skills_raw = _get_skill_scores(interview_id)
    strengths_raw, weaknesses_raw = _classify_strengths_and_weaknesses(skills_raw)
    ai_comments = _get_ai_commentary(strengths_raw, weaknesses_raw)

    rec = "SELECTED" if final_percentage >= threshold else "REJECTED"

    strengths = [
        SkillAssessment(
            skill=s["name"],
            confidence_score=s["confidence_score"],
            importance_score=s["importance_score"],
            weighted_score=s["weighted"],
            commentary=ai_comments["strength_comments"].get(s["name"], "")
        )
        for s in strengths_raw
    ]

    weaknesses = [
        SkillAssessment(
            skill=s["name"],
            confidence_score=s["confidence_score"],
            importance_score=s["importance_score"],
            weighted_score=s["weighted"],
            commentary=ai_comments["weakness_comments"].get(s["name"], "")
        )
        for s in weaknesses_raw
    ]

    # Update interview status
    with get_db() as db:
        db.execute(
            "UPDATE interviews SET status='REPORTED' WHERE id=?",
            (interview_id,)
        )

    return FinalReport(
        report_generated_at=datetime.utcnow().isoformat(),
        final_score=total_score,
        final_percentage=round(final_percentage, 3),
        pass_threshold=threshold,
        recommendation=rec,
        recommendation_rationale=(
            "Candidate demonstrated skills above expectations for this role."
            if rec == "SELECTED" else
            "Candidate did not meet the strict skill depth and relevance threshold."
        ),
        strengths=strengths,
        weaknesses=weaknesses,
        anything_extra=ai_comments.get("anything_extra", "")
    )

from pydantic import BaseModel
from typing import List, Optional


class SkillAssessment(BaseModel):
    skill: str
    confidence_score: int
    importance_score: int
    weighted_score: int
    commentary: str


class FinalReport(BaseModel):
    report_generated_at: str
    final_score: int
    final_percentage: float
    pass_threshold: float
    recommendation: str
    recommendation_rationale: str
    strengths: List[SkillAssessment]
    weaknesses: List[SkillAssessment]
    anything_extra: Optional[str] = ""

import json
from app.utils.pdf2text import extract_text_from_pdf
from app.database import get_db
from app.config import MAX_PDF_SIZE, OPENAI_API_KEY
from openai import OpenAI

def get_openai_client():
    return OpenAI(api_key=OPENAI_API_KEY)


import json
import re

from openai import OpenAI
from app.config import OPENAI_API_KEY


def clean_json(text: str) -> str:
    """Remove markdown, weird prefixes, and attempt to isolate JSON object."""

    # Strip markdown fences
    cleaned = re.sub(r"```(json)?", "", text)
    cleaned = cleaned.strip("` \n\t")

    # Extract content between { ... }
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    return cleaned


def analyze_resume(resume_text: str) -> dict:
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
You are an expert technical recruiter. Analyze the resume text below
and extract a detailed candidate profile.

Resume:
{resume_text}

Respond ONLY with valid JSON matching this structure:

{{
  "candidate_name": "string or Unknown",
  "domain": "Primary domain",
  "experience_level": "Junior/Mid-Level/Senior",
  "years_of_experience": int,
  "key_skills": [
    {{"name": "Skill1", "importance_score": int}}
  ],
  "expertise_areas": [
    "area1"
  ]
}}

STRICT RULES:
- Return ONLY JSON. No extra commentary.
- No code fences (```).
- No trailing commas.
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Respond only with valid JSON. No markdown."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    raw = response.choices[0].message.content
    cleaned = clean_json(raw)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        raise ValueError(f"Resume AI returned invalid JSON: {cleaned[:100]}...")


def process_resume_upload(user_id: int, file_bytes: bytes) -> int:
    """
    Full processing:
    - Validate size
    - Extract text
    - Analyze profile via LLM
    - Create Interview record
    - Store JSON profile
    """
    if len(file_bytes) > MAX_PDF_SIZE:
        raise ValueError("PDF exceeds 3MB limit")

    # Extract all text for resume analysis
    resume_text = extract_text_from_pdf(file_bytes)
    if not resume_text:
        raise ValueError("Failed to read PDF text. Ensure it's text-based.")

    # Get profile JSON from AI
    candidate_profile = analyze_resume(resume_text)

    # Insert new interview
    with get_db() as db:
        cursor = db.execute(
            "INSERT INTO interviews (user_id, resume_blob, resume_text, status, candidate_profile) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, file_bytes, resume_text, "GENERATING_QUESTIONS", json.dumps(candidate_profile))
        )
        interview_id = cursor.lastrowid

    return interview_id, candidate_profile

import json
from openai import OpenAI
from app.config import OPENAI_API_KEY, get_question_limits
from app.database import get_db


def get_openai_client():
    return OpenAI(api_key=OPENAI_API_KEY)


def get_global_job_description():
    """Fetch the single global Job Description text."""
    with get_db() as db:
        row = db.execute("SELECT content FROM job_description").fetchone()
        return row["content"] if row else ""


def get_candidate_profile(interview_id: int) -> dict:
    """Return parsed profile for this interview session."""
    with get_db() as db:
        row = db.execute(
            "SELECT candidate_profile FROM interviews WHERE id = ?",
            (interview_id,)
        ).fetchone()
        return json.loads(row["candidate_profile"]) if row else {}


def save_consequential_questions(interview_id: int, questions: list):
    """
    Store generated consequential questions in the DB, unasked initially.
    """
    with get_db() as db:
        for q in questions:
            db.execute(
                "INSERT INTO questions (interview_id, question_text, source_type) VALUES (?, ?, ?)",
                (interview_id, q, "consequential")
            )


def generate_consequential_questions(interview_id: int, count: int = 8):
    """
    Generate the first set of challenging multi-skill questions.
    These are based on:
    - Resume skill importance
    - Expertise area
    - Job Description alignment
    """
    profile = get_candidate_profile(interview_id)
    jd = get_global_job_description()

    prompt = f"""
You are an elite technical interviewer screening for top 5% talent.

Create {count} highly challenging, multi-skill, real-world scenario questions.

Base them on:
Candidate Profile: {json.dumps(profile)}
Job Description: {jd}

Rules:
- Output as a JSON array of strings
- Questions must test multiple skills together
- Hardest difficulty from the start
- No generic textbook questions
- Each question must require reasoning, decision-making, and tradeoffs
- JSON ONLY. No markdown.
"""

    response = get_openai_client().chat.completions.create(
        model="gpt-4o",
        temperature=0.6,
        messages=[
            {"role": "system", "content": "Respond with valid JSON only!"},
            {"role": "user", "content": prompt}
        ]
    )

    content = response.choices[0].message.content
    questions = json.loads(content)
    save_consequential_questions(interview_id, questions)


def get_last_answer(interview_id: int) -> dict:
    """
    Get the most recent answered question to use for follow-up generation.
    """
    with get_db() as db:
        return db.execute("""
            SELECT q.question_text, a.answer_text
            FROM answers a
            JOIN questions q ON q.id = a.question_id
            WHERE q.interview_id = ?
            ORDER BY a.id DESC
            LIMIT 1
        """, (interview_id,)).fetchone()


def generate_followup_question(interview_id: int) -> str:
    """
    Generate a deeper and harder follow-up question based on the last answer.
    Ensures proper DB storage as a string.
    """
    profile = get_candidate_profile(interview_id)
    last = get_last_answer(interview_id)
    jd = get_global_job_description()

    if not last:
        raise ValueError("Cannot generate follow-up: No previous answer.")

    last_question = last["question_text"]
    last_answer = last["answer_text"]

    prompt = f"""
You are an elite interviewer. Based on the previous Q&A below, generate ONE new question:

Previous Question:
{last_question}

Candidate Answer:
{last_answer}

Candidate Profile: {json.dumps(profile)}
Job Description: {jd}

Rules:
- The new question must escalate difficulty significantly
- It must integrate multiple advanced skills
- Require design-level reasoning and tradeoffs
- JSON ONLY. No markdown.
- Output as a JSON array of strings
    """

    response = get_openai_client().chat.completions.create(
        model="gpt-4o",
        temperature=0.8,
        messages=[
            {"role": "system", "content": "Respond with valid JSON only!"},
            {"role": "user", "content": prompt}
        ]
    )

    raw = response.choices[0].message.content
    try:
        next_q = json.loads(raw)
        if not isinstance(next_q, str):
            next_q = str(next_q)
    except Exception:
        # Last line fallback — ensure a string always goes into DB
        next_q = raw.strip()

    # Store into DB
    with get_db() as db:
        cursor = db.execute(
            "INSERT INTO questions (interview_id, question_text, source_type, asked) VALUES (?, ?, 'followup', 0)",
            (interview_id, next_q)
        )
        q_id = cursor.lastrowid

    return next_q

import json
from openai import OpenAI
from app.config import OPENAI_API_KEY
from app.database import get_db

client = OpenAI(api_key=OPENAI_API_KEY)


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

    response = client.chat.completions.create(
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
    Generate a deeper and harder follow-up question based on the candidate's last answer quality.
    Hardness scaling is applied: if the last answer was strong → make next much harder.
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
- It must integrate more than one advanced area from the resume
- Require design-level thinking and real-world tradeoffs
- Focus on finding weaknesses or pushing boundaries
- Response: JSON string only (not array), no markdown
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.8,
        messages=[
            {"role": "system", "content": "Return valid JSON only, as a single string"},
            {"role": "user", "content": prompt}
        ]
    )

    new_q = json.loads(response.choices[0].message.content)

    # Store into DB as a new follow-up question
    with get_db() as db:
        db.execute(
            "INSERT INTO questions (interview_id, question_text, source_type) VALUES (?, ?, 'followup')",
            (interview_id, new_q)
        )

    return new_q

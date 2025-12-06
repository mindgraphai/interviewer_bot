import os
from dotenv import load_dotenv

# Load .env from base directory
load_dotenv()

# Global configurations
DATABASE_URL = "sqlite:///./interviewer.db"

# OpenAI global API key (admin managed)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Max size for resume uploads (bytes)
MAX_PDF_SIZE = 3 * 1024 * 1024  # 3MB limit

if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY in .env")


from app.database import get_db

def get_question_limits():
    """
    Returns:
      total_questions, consequential_max, followup_max
    """
    with get_db() as db:
        row = db.execute("""
            SELECT total_questions, consequential_max, followup_max
            FROM question_config
            LIMIT 1
        """).fetchone()

    if not row:
        # Default fallback if DB empty
        return 5, 3, 2

    return (
        row["total_questions"],
        row["consequential_max"],
        row["followup_max"]
    )

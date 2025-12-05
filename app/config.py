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

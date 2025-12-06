import sqlite3
from contextlib import contextmanager

DATABASE_NAME = "interviewer.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # dict-like access to columns
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        # Users table
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            api_key TEXT UNIQUE NOT NULL
        );
        """)

        # Global Job Description
        db.execute("""
        CREATE TABLE IF NOT EXISTS job_description (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Interview Session
        # Interview Session
        db.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resume_blob BLOB,
            resume_text TEXT,
            status TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """)

        # Add candidate_profile column if not exists
        existing_cols = [col["name"] for col in db.execute("PRAGMA table_info(interviews);")]
        if "candidate_profile" not in existing_cols:
            db.execute("ALTER TABLE interviews ADD COLUMN candidate_profile TEXT;")


        # Skills``
        db.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interview_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            importance_score INTEGER CHECK(importance_score BETWEEN 1 AND 100),
            confidence_score INTEGER CHECK(confidence_score BETWEEN 1 AND 100),
            FOREIGN KEY (interview_id) REFERENCES interviews(id)
        );
        """)

        # Questions
        db.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interview_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            source_type TEXT CHECK(source_type IN ('consequential','followup')),
            asked BOOLEAN DEFAULT 0,
            FOREIGN KEY (interview_id) REFERENCES interviews(id)
        );
        """)

        # Answers
        db.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            answer_text TEXT,
            score INTEGER,
            retry_used BOOLEAN DEFAULT 0,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        );
        """)

        # Interview State Enum (values we enforce manually)
        # UPLOADED_RESUME, GENERATING_QUESTIONS, IN_PROGRESS, COMPLETED, FAILED, ABORTED

        print("Database initialized successfully.")

        # db.execute("""
        # ALTER TABLE interviews
        # ADD COLUMN candidate_profile TEXT;
        # """)

        db.execute("""
        CREATE TABLE IF NOT EXISTS question_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_questions INTEGER DEFAULT 5,
            consequential_max INTEGER DEFAULT 3,
            followup_max INTEGER DEFAULT 2
        );
        """)

        existing = db.execute("SELECT COUNT(*) cnt FROM question_config").fetchone()["cnt"]
        if existing == 0:
            db.execute("INSERT INTO question_config (total_questions, consequential_max, followup_max) VALUES (5, 3, 2)")
            
        # Seed Admin User
        admin_exists = db.execute("SELECT COUNT(*) cnt FROM users WHERE username='admin'").fetchone()["cnt"]
        if admin_exists == 0:
            from app.utils.security import hash_password, generate_api_key
            hashed = hash_password("admin")
            key = generate_api_key()
            db.execute(
                "INSERT INTO users (username, password, api_key) VALUES (?, ?, ?)",
                ("admin", hashed, key)
            )
            print(f"Admin user created. Key: {key}")

        # Pass Threshold Table
        db.execute("""
        CREATE TABLE IF NOT EXISTS pass_threshold (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            value REAL DEFAULT 0.7  -- 70% default cutoff score
        );
        """)

        # Ensure 1 config row always exists
        exists = db.execute("SELECT COUNT(*) AS cnt FROM pass_threshold").fetchone()["cnt"]
        if exists == 0:
            db.execute("INSERT INTO pass_threshold (value) VALUES (0.7)")

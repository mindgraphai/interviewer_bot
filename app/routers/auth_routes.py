from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.utils.security import hash_password, verify_password, generate_api_key

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup")
def signup(username: str, password: str):
    api_key = generate_api_key()

    with get_db() as db:
        try:
            db.execute(
                "INSERT INTO users (username, password, api_key) VALUES (?, ?, ?)",
                (username, hash_password(password), api_key)
            )
        except Exception:
            raise HTTPException(status_code=409, detail="Username already exists")

    return {"message": "User created successfully", "api_key": api_key}


@router.post("/login")
def login(username: str, password: str):
    with get_db() as db:
        row = db.execute(
            "SELECT id, password, api_key FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        stored_hash = row["password"]
        if not verify_password(password, stored_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")

    return {"message": "Login successful", "api_key": row["api_key"]}

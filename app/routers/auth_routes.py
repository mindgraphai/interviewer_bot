from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.utils.security import hash_password, generate_api_key
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])

class SignupRequest(BaseModel):
    username: str
    password: str

@router.post("/signup")
def signup(data: SignupRequest):
    with get_db() as db:
        try:
            hashed_pw = hash_password(data.password)
            api_key = generate_api_key()
            db.execute(
                "INSERT INTO users (username, password, api_key) VALUES (?, ?, ?)",
                (data.username, hashed_pw, api_key)
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Username already exists")
    
    return {"api_key": api_key}



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

from fastapi import Header, HTTPException
from app.database import get_db

async def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="API Key missing")

    with get_db() as db:
        row = db.execute(
            "SELECT id, username FROM users WHERE api_key = ?",
            (x_api_key,)
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    return {"user_id": row["id"], "username": row["username"]}

import bcrypt
import os

# -------- Password Hashing -------- #

def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode(), salt)
    return hashed.decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


# -------- API Key Generation -------- #

def generate_api_key() -> str:
    # 32 random bytes → 64 char hex string (base16)
    return os.urandom(32).hex()

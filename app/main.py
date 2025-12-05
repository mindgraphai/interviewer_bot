from fastapi import FastAPI
from app.database import init_db
from app.routers import auth_routes

app = FastAPI(
    title="AI Interviewer Backend",
    version="1.0.0"
)

init_db()  # ensures database tables exist
app.include_router(auth_routes.router)

@app.get("/")
def home():
    return {"status": "running"}

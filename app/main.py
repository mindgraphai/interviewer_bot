from fastapi import FastAPI
from app.database import init_db

from app.routers import (
    auth_routes,
    admin_routes,
    interview_routes,
    question_routes,
    report_routes
)

app = FastAPI(
    title="AI Interviewer Backend",
    version="1.0.0"
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()  # ensures database tables exist

# Include all routers
app.include_router(auth_routes.router)
app.include_router(admin_routes.router)
app.include_router(interview_routes.router)
app.include_router(question_routes.router)
app.include_router(report_routes.router)
app.include_router(report_routes.router)

@app.get("/")
def home():
    return {"status": "running"}

import os
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, DATABASE_NAME
from app.config import OPENAI_API_KEY

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Ensure a clean DB for test run
    if os.path.exists(DATABASE_NAME):
        os.remove(DATABASE_NAME)
    init_db()
    yield
    if os.path.exists(DATABASE_NAME):
        os.remove(DATABASE_NAME)


def test_full_interview_flow():
    # 1️⃣ Sign up user
    signup_resp = client.post("/auth/signup", json={
        "username": "test_user",
        "password": "test_pwd"
    })
    assert signup_resp.status_code == 200
    api_key = signup_resp.json()["api_key"]
    headers = {"X-API-Key": api_key}

    # 2️⃣ Admin login to set JD
    admin_login = client.post("/auth/signup", json={
        "username": "admin",
        "password": "admin"
    })
    assert admin_login.status_code == 200
    admin_key = admin_login.json()["api_key"]
    admin_headers = {"X-API-Key": admin_key}

    # 3️⃣ Set job description via admin
    with open("tests/jd.pdf", "rb") as jd_file:
        jd_resp = client.post(
            "/admin/set_job_description",
            headers=admin_headers,
            files={"file": ("jd.pdf", jd_file, "application/pdf")}
        )
    assert jd_resp.status_code == 200

    # 4️⃣ Upload resume
    with open("tests/resume.pdf", "rb") as resume:
        resume_resp = client.post(
            "/interviews/upload_resume",
            headers=headers,
            files={"file": ("resume.pdf", resume, "application/pdf")}
        )
    print("Resume Response:", resume_resp.json())

    assert resume_resp.status_code == 200
    interview_id = resume_resp.json()["interview_id"]

    # 5️⃣ Fetch first question
    q_resp = client.get(f"/questions/next/{interview_id}", headers=headers)
    assert q_resp.status_code == 200
    question = q_resp.json()["question"]
    assert question != ""

    # Loop through 15 Q&A
    for _ in range(15):
        ans_payload = {
            "answer": "Valid strong technical answer"
        }
        a_resp = client.post(
            f"/questions/{q_resp.json().get('id', 1)}/answer",  
            headers=headers,
            json=ans_payload
        )
        print("\nAnswer Response:", a_resp.json())

        assert a_resp.status_code == 200

        if a_resp.json().get("done"):
            break
        
        next_q = a_resp.json().get("next_question")
        assert next_q is not None
        question = next_q

    # 6️⃣ Final report
    report_resp = client.get(f"/report/{interview_id}", headers=headers)
    assert report_resp.status_code == 200

    report = report_resp.json()
    assert "final_score" in report
    assert "strengths" in report
    assert "weaknesses" in report
    assert "recommendation" in report
    assert report["final_score"] >= 15  # minimum possible

# AI Interviewer Bot — Backend

An AI-powered technical interviewer designed to evaluate and filter top 5% candidates through:

* Resume-based dynamic interview generation
* Adaptive follow-up questioning
* Strict evaluation + retry rules
* Skill-confidence scoring engine
* JD-aligned final recommendation report

---

## 🧱 Tech Stack

| Component    | Technology             |
| ------------ | ---------------------- |
| Backend      | FastAPI                |
| Database     | SQLite3                |
| LLM Provider | OpenAI GPT-4o          |
| Auth         | Custom API Key-based   |
| Docs         | OpenAPI via Swagger UI |

---

## 🚀 Quickstart

Install dependencies:

```bash
pip install -r requirements.txt
```

Run server:

```bash
uvicorn app.main:app --reload
```

API Docs:

* Swagger UI → [http://localhost:8000/docs](http://localhost:8000/docs)
* ReDoc → [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🔐 Authentication

After signup/login:
Include in every request:

```
X-API-Key: <api_key>
```

---

## 🧪 Interview Flow

1️⃣ Upload resume → `/interviews/upload_resume`
2️⃣ Get questions → `/questions/next/{interview_id}`
3️⃣ Answer and progress → `/questions/{qid}/answer`
4️⃣ After 15 Qs → fetch report → `/report/{interview_id}`

---

## 👑 Admin Operations

Set JD:

```bash
POST /admin/set_job_description
```

Set pass threshold (0–1):

```bash
POST /admin/set_threshold
```

---

## 📂 Project Structure

```
app/
 ├─ auth/
 ├─ services/
 ├─ models/
 ├─ utils/
 ├─ database.py
 ├─ security.py
 ├─ main.py
```

---

## 🧠 Key Features

✔ Resume parsing
✔ 8 consequential + 7 follow-up Qs
✔ Hardness scaling
✔ Retry once if vague
✔ Weighted skill analysis
✔ AI-finalized hiring decision 🎯

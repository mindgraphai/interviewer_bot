# OpenAPI API Specification — AI Technical Interview System

## Authorization

All endpoints except `/auth/signup` & `/auth/login` require:
`X-API-Key: <key>`

---

## Auth

### POST /auth/signup

Signup with username + password
Response: `{ "api_key": "..." }`

### POST /auth/login

Login with credentials
Response: `{ "api_key": "..." }`

---

## Admin

### POST /admin/set_job_description

Body: `{ "content": "<JD text>" }`
Requires admin API key

### POST /admin/set_threshold

Body:

{
  "value": 0.85
}
```

### POST /admin/set_question_config

Body:

```
{
  "total_questions": 15,
  "consequential_max": 8,
  "followup_max": 7
}
```

### GET /admin/get_question_config

Returns:

```
{
  "total_questions": 15,
  "consequential_max": 8,
  "followup_max": 7
}
```

### GET /admin/candidates

Returns list of candidates:

```
[
  {
    "id": 1,
    "user_id": 101,
    "name": "john_doe",
    "score": 4.2,
    "domain": "General",
    "status": "COMPLETED"
  }
]
```

### POST /admin/set_job_description_content

Body: `{"content": "..."}`

---

## Interviews

### POST /interviews/upload_resume

Upload PDF file (`multipart/form-data`)
Response:

```
{
  "message": "...",
  "interview_id": 10
}
```

---

## Questions

### GET /questions/config

Returns the configured question limits:

```
{
  "total_questions": 15,
  "consequential_max": 8,
  "followup_max": 7
}
```

### GET /questions/next/{interview_id}

Returns next question

```
{
  "question": "...",
  "done": false
}
```

### POST /questions/{question_id}/answer

Evaluate answer + return next question if valid

```
{
  "message": "Answer evaluated",
  "retry_required": false,
  "score": 5,
  "feedback": "Great depth",
  "next_question": "..."
}
```

If retry needed:

```
{
  "retry_required": true,
  "feedback": "Too vague"
}
```

---

## Final Report

### GET /report/{interview_id}

Returns FinalReport model:

```
{
  "report_generated_at": "...",
  "final_score": 72,
  "final_percentage": 0.92,
  "pass_threshold": 0.85,
  "recommendation": "SELECTED",
  "strengths": [...],
  "weaknesses": [...],
  "anything_extra": "..."
}
```

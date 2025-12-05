sequenceDiagram
    participant U as User / Frontend
    participant API as FastAPI Backend
    participant DB as SQLite3
    participant AI as OpenAI Model

    Note over U: 1️⃣ User signs up / logs in
    U->>API: POST /auth/signup or /auth/login
    API->>DB: Store / Verify user + API key
    DB-->>API: OK
    API-->>U: {api_key}

    Note over U,API: 2️⃣ Upload Resume
    U->>API: POST /interviews/upload_resume (PDF + api_key)
    API->>DB: Save PDF, status="GENERATING_QUESTIONS"
    API->>AI: Analyze Resume (extract candidate profile JSON)
    AI-->>API: Profile JSON
    API->>DB: Store candidate_profile JSON
    API-->>U: {interview_id}

    Note over API: Consequential question generation may run<br/>on-demand for now (Celery later)

    Note over U,API: 3️⃣ Interview start (fetch next question)
    U->>API: GET /questions/next/{interview_id}
    API->>DB: Fetch first consequential Q
    DB-->>API: Q1
    API-->>U: {question}

    Note over U,API,AI: 4️⃣ Answer and evaluate
    U->>API: POST /questions/{qid}/answer
    API->>AI: Evaluate + Skill Confidence Scoring
    AI-->>API: JSON evaluation
    API->>DB: Store answer + score <br/>retry if vague
    API-->>U: {
        score,
        feedback,
        retry_required?,
        next_question?
    }

    Loop Mixed sequence until 15 total questions
        alt Follow-up needed
            API->>AI: Generate deeper/harder Q
        else Consequential unasked left
            API->>DB: Fetch next consequential
        end
        API-->>U: {next_question}
    end

    Note over U,API: 5️⃣ After Q15 completion
    U->>API: POST /questions/{qid}/answer
    API->>DB: Mark interview COMPLETED
    API-->>U: {
        done: true,
        message: "Interview completed. Fetch report."
    }

    Note over U,API: 6️⃣ Getting Final Report
    U->>API: GET /report/{interview_id}
    API->>AI: Generate strengths/weaknesses + rationale
    AI-->>API: Final report JSON
    API->>DB: Set status="REPORTED"
    API-->>U: Full report JSON

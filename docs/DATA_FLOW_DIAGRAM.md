# HealthTech Platform - End-to-End Data Flow Diagrams (Week 6 Final Capstone)

## 1. End-to-End Demonstration Flow
`User Signup → Profile Completion → Prediction → Cluster Visualization → Grounded LLM Policy Answer → Agent Tool Call → Human Approval → Audit Trail`

```mermaid
sequenceDiagram
    autonumber
    actor Member as Patient / Member
    participant UI as Next.js Frontend
    participant Gateway as Django API Gateway
    participant ProfileDB as PostgreSQL (Profiles & Audit)
    participant ML as ML Inference Core
    participant RAG as Advanced RAG Engine
    participant Agent as Multi-Step Agent Planner
    participant Store as Mock Appointment Store

    %% 1. Signup & Profile Completion
    Note over Member, ProfileDB: Phase 1: Authentication & Profile Completion
    Member->>UI: Submit Signup & Login Credentials
    UI->>Gateway: POST /api/auth/login/
    Gateway-->>UI: Set HttpOnly JWT Cookies (access_token, refresh_token)
    Member->>UI: Enter Demographics & Emergency Contact
    UI->>Gateway: PUT /api/profiles/me/
    Gateway->>ProfileDB: Upsert Profile & Append to audit_events table
    Gateway-->>UI: 200 OK (Profile Status: COMPLETE 100%)

    %% 2. Supervised No-Show Prediction
    Note over Member, ML: Phase 2: Supervised ML Inference
    Member->>UI: Select "Single Prediction" Tab & Enter Appointment Features
    UI->>Gateway: POST /api/v1/predict/
    Gateway->>ML: Evaluate Input with Cached Pipeline & Band Cutpoints
    ML-->>Gateway: Risk Score: 0.18, Risk Band: "LOW", Disclaimer
    Gateway-->>UI: 200 OK (Render Color-coded Risk Badge)

    %% 3. Unsupervised Clustering Visualization
    Note over Member, ML: Phase 3: Unsupervised Patient Segmentation
    Member->>UI: Select "Patient Clustering" Tab
    UI->>Gateway: GET /api/v1/clusters/
    Gateway->>ML: Fetch Cached 2D PCA & K-Means (k=6) Centroids
    Gateway-->>UI: 200 OK (Render Interactive 2D PCA Scatterplot)

    %% 4. Grounded LLM Policy FAQ Answer
    Note over Member, RAG: Phase 4: Grounded Policy Retrieval
    Member->>UI: Ask: "What is the cancellation policy?"
    UI->>Gateway: POST /api/v1/llm/faq/
    Gateway->>RAG: Hybrid Search (BM25 + TF-IDF RRF) over Policies
    RAG-->>Gateway: Top Passages with doc_id & Section Quotes
    Gateway-->>UI: 200 OK (Grounded Response with Verifiable Citations)

    %% 5. Agent Workflow with Human Write Approval Gate
    Note over Member, Store: Phase 5: Controlled Multi-Step Agent Write Gate
    Member->>UI: Request: "Book an appointment with cardiology next Tuesday at 11:00 am"
    UI->>Gateway: POST /api/v1/agents/workflow/
    Gateway->>Agent: Execute Multi-Step Planner (Plan -> Tool Select -> Validate)
    Agent->>RAG: Tool 1: search_approved_documents("cardiology booking policy")
    Agent->>Store: Tool 2: check_appointment_availability("cardiology", "2026-11-17")
    Agent->>Agent: Tool 5: draft_mock_appointment (Stops before writing)
    Agent-->>Gateway: Status: NEEDS_CONFIRMATION, Idempotency Key: idem-wf-992
    Gateway-->>UI: Render Confirmation Modal & Human-in-the-Loop Gate
    Member->>UI: Clicks "Confirm & Schedule Appointment"
    UI->>Gateway: POST /api/v1/agents/workflow/ (human_confirmed=True, idem-wf-992)
    Gateway->>Agent: Validate Idempotency & Execute Write
    Agent->>Store: Persist Appointment Draft as CONFIRMED
    Agent->>ProfileDB: Log Agent Action to Admin Audit Records
    Gateway-->>UI: Status: COMPLETED, Booking Confirmed Response
```

---

## 2. Model Drift Monitoring & Background Task Queue Flow

```mermaid
sequenceDiagram
    autonumber
    actor Admin as System Administrator
    participant AdminUI as Next.js Admin & Workbench UI
    participant Gateway as Django API Gateway
    participant Queue as BackgroundTaskQueue
    participant Worker as ThreadPool Worker
    participant Monitor as ModelMonitor

    Admin->>AdminUI: Trigger Document Re-Indexing or Batch Synthetic Run
    AdminUI->>Gateway: POST /api/v1/agents/jobs/
    Gateway->>Queue: submit_job(job_type, payload, max_retries=3)
    Queue-->>Gateway: Job Enqueued (job_id, status: "queued")
    Gateway-->>AdminUI: 202 Accepted (Job ID)

    par Asynchronous Execution
        Queue->>Worker: Dispatch Job Execution
        Worker->>Worker: Run task with exponential backoff on transient failure
        Worker->>Monitor: Record synthetic prediction outputs & inference latencies
        Worker-->>Queue: Mark Job as "succeeded" with execution metrics
    end

    AdminUI->>Gateway: GET /api/v1/agents/monitoring/metrics/
    Gateway->>Monitor: evaluate_drift() (Kolmogorov-Smirnov Test vs Baseline)
    Monitor-->>Gateway: KS p-value, Drift Flag (False), Latency percentiles
    Gateway-->>AdminUI: 200 OK (Render Real-Time Drift Gauges)
```

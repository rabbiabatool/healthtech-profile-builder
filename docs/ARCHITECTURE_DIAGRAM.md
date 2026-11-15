# HealthTech Platform - Full System Architecture (Week 6 Final Capstone)

## High-Level Architectural Topology

```mermaid
flowchart TD
    subgraph ClientLayer ["Client & User Layer"]
        UserBrowser["User / Member Browser"]
        AdminBrowser["Administrator Browser"]
        ExternalClient["External REST / OpenAPI Client"]
    end

    subgraph FrontendApp ["Frontend Application (Next.js 14+ / React 19)"]
        UI_Router["Next.js App Router (app/)"]
        UI_Auth["Auth & Session Guards (JWT Cookies / Admin Session)"]
        UI_Workbench["ML & AI Workbench Tabs (NoShowPredictor)"]
        UI_AdminPortal["Admin Dashboard & Audit Logs (/admin/audit)"]
    end

    subgraph APIGateway ["Security & Gateway Layer (Django 5.2)"]
        ReqIdMiddleware["Structured Logging & Request-ID Middleware (X-Request-ID)"]
        CSRFMiddleware["CSRF Header Validation (X-CSRFToken)"]
        DualAuth["Dual Authenticator: CookieJWTAuthentication + AdminSession"]
        RBAC["Role-Based Access Control (IsStandardUser vs IsAdminRole)"]
        HealthProbes["Observability Probes: /health & /ready"]
    end

    subgraph CoreServices ["Backend Application Services"]
        ProfileService["Profiles & Demographics CRUD Service"]
        AuditService["Append-Only Audit Event Service"]
        MLService["Supervised ML Inference Service (NoShowPredictView)"]
        ClusteringService["Unsupervised Behavioral Segmentation Service"]
        RAGService["Advanced RAG Engine (BM25 + TF-IDF RRF)"]
        AgentPlanner["Multi-Step Agent Planner & Tool Orchestrator"]
    end

    subgraph ToolEcosystem ["Controlled Agent Tools & Guardrails"]
        Tool1["Tool 1: search_approved_documents"]
        Tool2["Tool 2: check_appointment_availability"]
        Tool3["Tool 3: request_supervised_prediction"]
        Tool4["Tool 4: retrieve_cluster_summaries"]
        Tool5["Tool 5: draft_mock_appointment (Write Protected)"]
        HumanGate{{"Human Confirmation Gate (Idempotency Key)"}}
    end

    subgraph BackgroundWorker ["Asynchronous Processing Layer"]
        TaskQueue["BackgroundTaskQueue (ThreadPoolWorker)"]
        IndexJob["Document Re-indexing Job"]
        BatchJob["Batch Synthetic Predictions Job"]
        DriftMonitor["Model Drift KS-Test & Latency Telemetry"]
    end

    subgraph StorageLayer ["Persistence & Artifact Layer"]
        PostgresDB[("PostgreSQL 16 DB (health_profiles, audit_events, users)")]
        ModelArtifacts["Serialized Model Artifacts (model.joblib, metadata.json)"]
        VectorCorpus["Policy Corpus Chunks & Inverted BM25 Index"]
    end

    UserBrowser --> UI_Router
    AdminBrowser --> UI_Router
    ExternalClient --> APIGateway

    UI_Router --> UI_Workbench
    UI_Router --> UI_AdminPortal
    UI_Router --> APIGateway

    APIGateway --> ReqIdMiddleware
    ReqIdMiddleware --> CSRFMiddleware
    CSRFMiddleware --> DualAuth
    DualAuth --> RBAC
    RBAC --> CoreServices

    ProfileService --> PostgresDB
    AuditService --> PostgresDB
    MLService --> ModelArtifacts
    ClusteringService --> ModelArtifacts
    RAGService --> VectorCorpus

    AgentPlanner --> Tool1
    AgentPlanner --> Tool2
    AgentPlanner --> Tool3
    AgentPlanner --> Tool4
    AgentPlanner --> Tool5

    Tool5 --> HumanGate
    HumanGate -->|Approved| PostgresDB
    HumanGate -->|Rejected| AgentPlanner

    CoreServices --> TaskQueue
    TaskQueue --> IndexJob
    TaskQueue --> BatchJob
    DriftMonitor --> PostgresDB
```

---

## Architecture Highlights
1. **Zero-Trust Multi-Layer Security**: Authentication, CSRF headers, and Role-Based Access Control (RBAC) are verified on every request at the view layer.
2. **Deterministic Model Caching**: In-memory caching with filesystem fingerprinting prevents repeated model deserialization, reducing inference latency by over 90%.
3. **Hybrid RAG with Reciprocal Rank Fusion (RRF)**: Combines exact BM25 keyword matching with sublinear TF-IDF cosine semantics, achieving 95% Recall@3.
4. **Controlled Human-in-the-Loop Agent Workflows**: Any write action halts execution, creates an immutable pending draft with an idempotency key, and requires explicit user approval before execution.

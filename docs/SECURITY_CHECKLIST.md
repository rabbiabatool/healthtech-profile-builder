# HealthTech Platform Security & Compliance Checklist (Week 6 Final Capstone)

## Overview & Scope
This checklist details the architectural safeguards, permission controls, and automated regression defenses implemented across the HealthTech learning platform (Weeks 1 through 6).

---

## 1. Authentication & Session Management
- [x] **Dual Authentication Schemes**: Separate authentication paths for Standard Users (short-lived Cookie JWT) and Administrators (HttpOnly server-side session cookies).
- [x] **Secure Cookie Flags**: `HttpOnly=True`, `SameSite=Lax`, and `Secure=True` enforced in production (`settings_prod.py`).
- [x] **Token Lifecycle**: JWT access token lifetime limited to 10 minutes; refresh token rotation and blacklisting enabled (`rest_framework_simplejwt.token_blacklist`).
- [x] **Automated Test Coverage**: `backend/accounts/tests.py`, `backend/tests/test_admin_auth.py`, `backend/tests/test_auth_user.py`.

---

## 2. Authorization & Privilege Matrix (RBAC)
- [x] **Strict Privilege Matrix**: Enforced at the Django REST Framework view layer via `permission_classes = [IsStandardUser]` and `permission_classes = [IsAdminRole]`.
- [x] **No Role Confusion**: Admins cannot access member-only ML prediction endpoints (`NoShowPredictView` returns 403 Forbidden to Admins). Standard users cannot view administrative audit logs or trigger admin jobs.
- [x] **Cross-User Data Isolation (IDOR Defense)**: Profile and emergency contact queries strictly filter on `user=request.user` or `profile=request.user.profile`.
- [x] **Automated Test Coverage**: `backend/tests/test_privilege_matrix.py`, `backend/tests/test_admin_profiles.py`, `backend/predictions/tests/test_Api.py`.

---

## 3. CSRF & Transport Security
- [x] **CSRF Protection**: Every state-changing API request (`POST`, `PUT`, `PATCH`, `DELETE`) requires an `X-CSRFToken` header matching the HttpOnly cookie token.
- [x] **HTTPS / HSTS**: Production settings enforce `SECURE_SSL_REDIRECT = True`, `SECURE_HSTS_SECONDS = 31536000` (1 year), and `X_FRAME_OPTIONS = "DENY"`.
- [x] **CORS & Host Allowlist**: Strict `DJANGO_ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` prevent host-header injection and unauthorized cross-origin requests.

---

## 4. Input Validation & Schema Boundaries
- [x] **Pydantic & DRF Serializer Validation**: All prediction inputs, profile fields, and agent queries are strictly type-checked against defined schema ranges (e.g. `age` bounded [0, 120], `lead_time_days` [0, 365]).
- [x] **Metadata Validation Before Cache**: ML model registry cutpoints (`HIGH`, `MEDIUM`) validated as finite numbers with non-empty schemas and bounded range `[0, 1]` before entering the cache.
- [x] **Safe 503 Fallbacks**: Invalid or unavailable models fail gracefully with HTTP 503 (`ModelUnavailable`) without leaking stack traces or unhandled 500 exceptions.
- [x] **Automated Test Coverage**: `backend/predictions/tests/test_serializers.py`, `backend/mlcore/tests/test_ml_registry.py`.

---

## 5. Defense Against Prompt Injection & Adversarial Content
- [x] **Pre-Execution Guardrails**: User queries scanned for system prompt overrides, prompt injection patterns, and jailbreak phrasing (`backend/agents/structured_llm.py`).
- [x] **Retrieved Context Isolation**: Content retrieved from RAG policies is wrapped in strict delimiter boundaries and cannot execute instructions.
- [x] **Non-Clinical Guardrail**: Any attempt to elicit clinical diagnosis or prescription advice triggers a mandatory canned refusal directing the user to a licensed healthcare professional.
- [x] **Automated Test Coverage**: `backend/agents/tests_phase2.py::test_prompt_injection_detection`, `backend/tests/test_week6_resilience_security.py::test_agent_prompt_injection_defense`.

---

## 6. Controlled Agent Writes & Human Confirmation Gate
- [x] **Server-Side Tool Authorization**: Tool execution authorization is checked at runtime on the server; the LLM prompt is never trusted to enforce security boundaries.
- [x] **Explicit Human-in-the-Loop Confirmation**: Any write tool (`draft_mock_appointment`) creates an immutable pending draft and halts the workflow with `status: NEEDS_CONFIRMATION`. Execution only proceeds after explicit user confirmation with matching idempotency key.
- [x] **Idempotency Keys**: Scheduled writes enforce unique idempotency keys (`idem-wf-<id>`) to prevent double-booking or replay attacks.
- [x] **Automated Test Coverage**: `backend/agents/tests_phase3.py::test_tool_5_schedule_mock_appointment_write_protection`, `backend/tests/test_week6_resilience_security.py::test_agent_rejects_unauthorized_write_without_confirmation`.

---

## 7. Secrets Management & PII Redaction
- [x] **Secret Isolation**: All credentials, secret keys (`DJANGO_SECRET_KEY`), and API keys (`GEMINI_API_KEY`) loaded strictly via environment variables. None hardcoded in code or committed to Git.
- [x] **PII Redaction Filter**: High-risk entities (credit card numbers, social security numbers, phone numbers, email addresses) automatically redacted from agent prompts, tool traces, and logged queries via `redact_sensitive_data()`.
- [x] **Immutable Audit Trail**: Changes to member demographics, logins, and administrative overrides written to append-only `audit_events` table without storing sensitive before/after field contents.
- [x] **Automated Test Coverage**: `backend/agents/tests_phase2.py::test_redact_sensitive_entities`, `backend/tests/test_audit_record_event.py`.

---

## 8. Summary of High-Risk Automated Regression Tests

| Category | Test Suite / Function | Target Protection |
| :--- | :--- | :--- |
| **RBAC** | `test_admins_are_forbidden_from_predictions` | Admin cannot access member prediction data |
| **IDOR** | `test_member_cannot_access_other_member_profile` | Cross-user data isolation |
| **Agent Writes** | `test_agent_rejects_unauthorized_write_without_confirmation` | Human confirmation gate enforced |
| **Adversarial** | `test_agent_prompt_injection_defense` | System prompt override prevention |
| **Metadata Integrity** | `test_malformed_metadata_gives_503_and_recovers` | Model tampering defense & recovery |
| **PII Redaction** | `test_run_structured_generation_redacts_pii` | Sanitizes phone, email, SSN from LLM |
| **Resilience** | `test_task_queue_transient_failure_recovery` | Exponential backoff prevents job loss |

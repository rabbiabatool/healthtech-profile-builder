"""Regression tests for Issue 4: Rate Limiting Denial & Evaluation Endpoint Protection.

Verifies:
1. Rate limit rejection is immediate (does not sleep and proceed).
2. Provider / LLM mock is NOT invoked when a request is rate-limited.
3. PolicyFAQView returns HTTP 429 with 'Retry-After: 1' on rate limit denial.
4. Evaluation endpoint GET is strictly read-only and never runs the evaluation runner.
5. Evaluation endpoint POST requires Admin session authentication and CSRF; members & anonymous are rejected.
6. Admin POST with CSRF executes evaluation and subsequent GET retrieves the persisted report.
"""
import time
from unittest.mock import MagicMock, patch
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from rag.engine import RateLimitExceeded, call_llm, check_rate_limit

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng!Pass#2026"
ADMIN_EMAIL = "admin_eval@greenleaf.test"
MEMBER_EMAIL = "member_eval@greenleaf.test"


@pytest.fixture
def real_admin(db):
    return User.objects.create_admin(
        email=ADMIN_EMAIL,
        password=PASSWORD,
        full_name="Admin Eval",
    )


@pytest.fixture
def real_member(db):
    return User.objects.create_user(
        email=MEMBER_EMAIL,
        password=PASSWORD,
        full_name="Member Eval",
    )


@pytest.fixture
def admin_session_client(real_admin):
    """APIClient logged in through the actual /api/admin/login endpoint with cookies preserved."""
    client = APIClient(enforce_csrf_checks=True)
    csrf_res = client.get("/api/admin/csrf")
    assert csrf_res.status_code == 200
    token = csrf_res.json()["csrfToken"]

    login_res = client.post(
        "/api/admin/login",
        {"email": ADMIN_EMAIL, "password": PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert login_res.status_code == 200
    assert "admin_session" in client.cookies
    assert "csrftoken" in client.cookies
    return client


@pytest.fixture
def member_jwt_client(real_member):
    """APIClient logged in through the actual /api/auth/user/login endpoint with JWT cookies preserved."""
    client = APIClient(enforce_csrf_checks=True)
    csrf_res = client.get("/api/auth/csrf")
    assert csrf_res.status_code == 200
    token = csrf_res.json()["csrfToken"]

    login_res = client.post(
        "/api/auth/user/login",
        {"email": MEMBER_EMAIL, "password": PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert login_res.status_code == 200
    assert "access_token" in client.cookies
    assert "csrftoken" in client.cookies
    return client


# ──────────────────────────────────────────────────────────
# Rate Limiting Tests
# ──────────────────────────────────────────────────────────

def test_check_rate_limit_immediate_denial_without_sleep():
    """Burst requests within window return False immediately without sleeping."""
    client_id = f"test_burst_{time.time()}"
    t0 = time.perf_counter()
    res1 = check_rate_limit(client_id=client_id, window_seconds=2)
    res2 = check_rate_limit(client_id=client_id, window_seconds=2)
    elapsed = time.perf_counter() - t0

    assert res1 is True
    assert res2 is False
    assert elapsed < 0.2, f"check_rate_limit slept! Elapsed: {elapsed:.3f}s"


def test_call_llm_raises_rate_limit_exceeded_and_skips_provider():
    """call_llm raises RateLimitExceeded immediately and does NOT invoke the provider."""
    mock_provider = MagicMock()
    mock_provider.return_value = {
        "answer": "Clinic opens at 8am.",
        "citations": ["hours.txt"],
        "confidence": "HIGH",
        "out_of_scope": False,
        "safety_flag": False,
    }

    passages = [{"doc_name": "hours.txt", "chunk_id": 0, "text": "Clinic opens at 8am."}]

    # Force check_rate_limit to return True then False
    with patch("rag.engine.check_rate_limit", side_effect=[True, False]):
        # First call succeeds
        res1 = call_llm(
            question="When do you open?",
            context_passages=passages,
            mock_provider=mock_provider,
            bypass_rate_limit=False,
        )
        assert res1["answer"] == "Clinic opens at 8am."
        assert mock_provider.call_count == 1

        # Second call must immediately raise RateLimitExceeded
        t0 = time.perf_counter()
        with pytest.raises(RateLimitExceeded):
            call_llm(
                question="When do you open again?",
                context_passages=passages,
                mock_provider=mock_provider,
                bypass_rate_limit=False,
            )
        elapsed = time.perf_counter() - t0

        # Provider must NOT have been called a second time
        assert mock_provider.call_count == 1
        assert elapsed < 0.1, f"call_llm slept on rate limit! Elapsed: {elapsed:.3f}s"


def test_faq_endpoint_returns_429_on_rate_limit(member_jwt_client):
    """POST /api/v1/llm/faq returns HTTP 429 with Retry-After header when rate limited."""
    csrf_token = member_jwt_client.cookies["csrftoken"].value

    with patch("rag.views.answer_question", side_effect=RateLimitExceeded("Too many requests")):
        res = member_jwt_client.post(
            "/api/v1/llm/faq",
            {"question": "What is the cancellation policy?"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert res.headers.get("Retry-After") == "1"
        assert res.json().get("error_code") == "RATE_LIMIT_EXCEEDED"


# ──────────────────────────────────────────────────────────
# Evaluation Endpoint Security & Read-Only GET Tests
# ──────────────────────────────────────────────────────────

def test_eval_get_is_strictly_read_only_and_does_not_execute_eval():
    """Unauthenticated GET returns saved report or 404 without executing evaluation."""
    client = APIClient()

    with patch("rag.evaluation.run_comparative_retrieval_evaluation") as mock_runner:
        res = client.get("/api/v1/llm/faq/evaluate")
        # Must not run the heavy evaluation harness
        mock_runner.assert_not_called()
        assert res.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


def test_eval_member_post_is_rejected(member_jwt_client):
    """Member POST is rejected with 403 Forbidden."""
    csrf_token = member_jwt_client.cookies["csrftoken"].value
    res = member_jwt_client.post(
        "/api/v1/llm/faq/evaluate",
        {"offline": True},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_eval_unauthenticated_post_is_rejected():
    """Unauthenticated POST is rejected with 401 or 403."""
    client = APIClient(enforce_csrf_checks=True)
    res = client.post(
        "/api/v1/llm/faq/evaluate",
        {"offline": True},
        format="json",
    )
    assert res.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


def test_eval_admin_post_missing_csrf_is_rejected(admin_session_client):
    """Admin POST without CSRF token is rejected with 403."""
    res = admin_session_client.post(
        "/api/v1/llm/faq/evaluate",
        {"offline": True},
        format="json",
        # Intentionally omit HTTP_X_CSRFTOKEN
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_eval_admin_post_with_csrf_executes_and_subsequent_get_reads_persisted(admin_session_client):
    """Admin POST with CSRF executes evaluation and subsequent GET retrieves the persisted report."""
    csrf_token = admin_session_client.cookies["csrftoken"].value

    mock_comp_result = {
        "strict": {
            "passed": 12,
            "total": 12,
            "pass_rate": 100,
            "total_approx_tokens": 1200,
            "results": [
                {
                    "id": "E01",
                    "category": "Hours",
                    "question": "When do you open?",
                    "expected_behavior": "Grounded answer",
                    "expected_facts": ["8am"],
                    "expected_citations": ["hours.txt"],
                    "actual_answer": "8am",
                    "actual_citations": ["hours.txt"],
                    "actual_confidence": "HIGH",
                    "actual_out_of_scope": False,
                    "actual_safety_flag": False,
                    "grounding_msg": "grounded",
                    "approximate_input_tokens": 50,
                    "approximate_output_tokens": 10,
                    "model_used": "test-double",
                    "pass": True,
                }
            ],
        },
        "relaxed": {
            "passed": 12,
            "total": 12,
            "pass_rate": 100,
            "total_approx_tokens": 2400,
            "results": [],
        },
        "eval_type": "offline_regression_test_double",
    }

    with patch("rag.evaluation.run_comparative_retrieval_evaluation", return_value=mock_comp_result) as mock_runner:
        post_res = admin_session_client.post(
            "/api/v1/llm/faq/evaluate",
            {"offline": True},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        assert post_res.status_code == status.HTTP_200_OK
        mock_runner.assert_called_once()
        data = post_res.json()
        assert "strict" in data
        assert "relaxed" in data

    # Subsequent GET retrieves saved report without re-running runner
    with patch("rag.evaluation.run_comparative_retrieval_evaluation") as mock_runner2:
        get_res = admin_session_client.get("/api/v1/llm/faq/evaluate")
        assert get_res.status_code == status.HTTP_200_OK
        mock_runner2.assert_not_called()
        get_data = get_res.json()
        assert "strict" in get_data or get_data.get("status") == "available"

"""Regression tests for Issue 1: Policy Governance Authentication with Real Admin Login.

Verifies that policy governance views (PolicyDocumentListView, PolicyDocumentApproveView,
PolicyDocumentRevokeView) recognize real admin sessions via AdminSessionAuthentication and enforce CSRF,
while members retain read-only access and are strictly forbidden from uploads/approvals.
Real APIClient authentication is used throughout (no force_authenticate).
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from rag.models import PolicyDocumentRecord

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng!Pass#2026"
ADMIN_EMAIL = "admin_gov@greenleaf.test"
MEMBER_EMAIL = "member_gov@greenleaf.test"


@pytest.fixture
def real_admin(db):
    return User.objects.create_admin(
        email=ADMIN_EMAIL,
        password=PASSWORD,
        full_name="Admin Governance",
    )


@pytest.fixture
def real_member(db):
    return User.objects.create_user(
        email=MEMBER_EMAIL,
        password=PASSWORD,
        full_name="Member Governance",
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
    return client


def test_real_admin_login_upload_and_approve_policy_workflow(admin_session_client, real_admin):
    """Real admin logs in, uploads a policy, and approves it using actual session and CSRF headers."""
    csrf_token = admin_session_client.cookies["csrftoken"].value
    doc_name = "digital_consent_policy.txt"
    content = "Digital consent must be confirmed prior to video telehealth consultations."

    # 1. Upload policy (starts PENDING)
    upload_res = admin_session_client.post(
        "/api/v1/llm/policies",
        {"doc_name": doc_name, "content": content},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert upload_res.status_code == status.HTTP_201_CREATED, upload_res.data
    assert upload_res.data["status"] == "PENDING"
    assert upload_res.data["doc_name"] == doc_name

    # Verify persisted in database
    record = PolicyDocumentRecord.objects.get(doc_id=doc_name)
    assert record.status == "PENDING"
    assert record.uploaded_by == ADMIN_EMAIL
    assert record.content == content

    # 2. Approve policy
    approve_res = admin_session_client.post(
        f"/api/v1/llm/policies/{doc_name}/approve",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert approve_res.status_code == status.HTTP_200_OK, approve_res.data
    assert approve_res.data["status"] == "APPROVED"
    assert approve_res.data["approved_by"] == ADMIN_EMAIL

    # Verify persisted approved state in database
    record.refresh_from_db()
    assert record.status == "APPROVED"
    assert record.approved_by == ADMIN_EMAIL
    assert record.approved_at is not None


def test_unauthenticated_upload_rejected():
    """Unauthenticated request cannot upload policy documents."""
    client = APIClient()
    res = client.post(
        "/api/v1/llm/policies",
        {"doc_name": "anon_policy.txt", "content": "Sample content longer than 20 chars"},
        format="json",
    )
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_member_upload_rejected(member_jwt_client):
    """Authenticated standard member cannot upload policy documents (403 Forbidden)."""
    csrf_token = member_jwt_client.cookies["csrftoken"].value
    res = member_jwt_client.post(
        "/api/v1/llm/policies",
        {"doc_name": "member_policy.txt", "content": "Member trying to upload policy text"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_member_approval_rejected(member_jwt_client, real_admin):
    """Authenticated standard member cannot approve policy documents (403 Forbidden)."""
    # Create a pending record in DB
    doc_name = "pending_sample.txt"
    PolicyDocumentRecord.objects.create(
        doc_id=doc_name,
        doc_name=doc_name,
        content="Sample pending document content for approval testing.",
        status="PENDING",
        uploaded_by=real_admin.email,
    )

    csrf_token = member_jwt_client.cookies["csrftoken"].value
    res = member_jwt_client.post(
        f"/api/v1/llm/policies/{doc_name}/approve",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_member_read_access_continues_to_work(member_jwt_client):
    """Authenticated standard member retains read-only policy access (200 OK on GET)."""
    res = member_jwt_client.get("/api/v1/llm/policies")
    assert res.status_code == status.HTTP_200_OK
    assert "policies" in res.data
    assert isinstance(res.data["policies"], list)


def test_missing_or_invalid_csrf_protection_rejected(admin_session_client):
    """Admin write operation without CSRF header is rejected with 403 Forbidden."""
    res = admin_session_client.post(
        "/api/v1/llm/policies",
        {"doc_name": "no_csrf.txt", "content": "Valid policy text longer than 20 characters"},
        format="json",
        # Intentionally omit HTTP_X_CSRFTOKEN
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_admin_cannot_access_member_only_endpoints(admin_session_client):
    """Admin session does not grant member-only permissions (e.g. member FAQ assistant)."""
    csrf_token = admin_session_client.cookies["csrftoken"].value
    res = admin_session_client.post(
        "/api/v1/llm/faq",
        {"question": "How do I book?"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    # Rejects admin session on member endpoint (401 or 403)
    assert res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

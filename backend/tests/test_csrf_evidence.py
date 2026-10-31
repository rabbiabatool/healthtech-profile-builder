"""
test_csrf_evidence.py
=====================
Verify that CSRF protection works correctly for both member and admin flows.

Evidence A: A state-changing request with a valid admin session but MISSING
            the CSRF token is rejected (403 CSRF Failed).

Evidence B: An otherwise valid state-changing request WITH the CSRF token
            passes CSRF validation (the request proceeds to business logic).
"""

import pytest
from rest_framework.test import APIClient

from accounts.models import User
from profiles.models import HealthProfile

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng!Pass#2026"


# ---------------------------------------------------------------------------
# Admin CSRF evidence
# ---------------------------------------------------------------------------


class TestAdminCSRFEvidence:
    """Verify CSRF on admin deactivation endpoint (a safe test operation)."""

    @pytest.fixture
    def admin_setup(self, admin, admin_login, user):
        """Log the admin in and return (client, profile_id)."""
        client = APIClient(enforce_csrf_checks=True)
        login_resp = admin_login(client)
        assert login_resp.status_code == 200, login_resp.json()
        profile = HealthProfile.objects.get(user=user)
        return client, profile.pk

    def test_admin_deactivation_without_csrf_token_is_rejected(self, admin_setup):
        """
        Evidence A: Missing CSRF token → 403.
        Endpoint: PATCH /api/admin/profiles/<id>/deactivate
        """
        client, profile_id = admin_setup
        url = f"/api/admin/profiles/{profile_id}/deactivate"
        # Do NOT pass X-CSRFToken header.
        response = client.patch(url, {}, format="json")
        assert response.status_code == 403, (
            f"Expected 403 for missing CSRF, got {response.status_code}: {response.json()}"
        )
        assert "csrf" in response.json().get("detail", "").lower() or \
               "CSRF" in response.json().get("detail", "")
        # Profile must remain ACTIVE (no mutation happened).
        assert HealthProfile.objects.get(pk=profile_id).status == "ACTIVE"

    def test_admin_deactivation_with_csrf_token_passes_validation(self, admin_setup):
        """
        Evidence B: Valid CSRF token → passes CSRF validation.
        The request proceeds to business logic and succeeds (200).
        """
        client, profile_id = admin_setup
        url = f"/api/admin/profiles/{profile_id}/deactivate"
        # Fetch a CSRF token.
        token = client.get("/api/admin/csrf").json()["csrfToken"]
        response = client.patch(url, {}, format="json", HTTP_X_CSRFTOKEN=token)
        assert response.status_code == 200, (
            f"Expected 200 with valid CSRF, got {response.status_code}: {response.json()}"
        )
        # Profile should now be INACTIVE.
        assert HealthProfile.objects.get(pk=profile_id).status == "INACTIVE"


# ---------------------------------------------------------------------------
# Member CSRF evidence
# ---------------------------------------------------------------------------


class TestMemberCSRFEvidence:
    """Verify CSRF on member demographics PATCH (a safe test operation)."""

    @pytest.fixture
    def member_setup(self, user, login):
        """Log the member in with CSRF enforcement and return the client."""
        client = APIClient(enforce_csrf_checks=True)
        login(client)
        return client

    def test_member_patch_without_csrf_token_is_rejected(self, member_setup):
        """
        Evidence A (member): Missing CSRF token on PATCH → 403.
        """
        client = member_setup
        response = client.patch(
            "/api/profiles/me/demographics",
            {"country": "Canada"},
            format="json",
        )
        assert response.status_code == 403

    def test_member_patch_with_csrf_token_passes_validation(self, member_setup):
        """
        Evidence B (member): Valid CSRF token on PATCH → passes validation (200).
        """
        client = member_setup
        token = client.get("/api/auth/csrf").json()["csrfToken"]
        response = client.patch(
            "/api/profiles/me/demographics",
            {"country": "Canada"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 200


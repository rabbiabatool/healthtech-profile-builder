"""
test_profile_lifecycle.py
=========================
Tests for root-profile creation (POST /api/profiles/me),
deletion (DELETE /api/profiles/me), and the full lifecycle sequence
described in the Week 2 feedback.

Lifecycle sequence under test
------------------------------
 1. Create a profile.
 2. Read the profile.
 3. Edit supported profile information.
 4. Delete the root profile.
 5. Verify that the profile is gone (404 on GET).
 6. Verify that the account remains (user still exists in DB).
 7. Verify that the deletion audit event retains the original profile ID.
 8. Re-create the profile.
 9. Verify that the new profile has a different identifier.
10. Verify that the old audit history remains intact.

Additional contracts tested
----------------------------
- Duplicate creation → 409
- Missing profile GET → 404
- Root GET is read-only (no auto-creation)
- Root PATCH → 405
- Cross-user denial
- Member / admin role restrictions
- PROFILE_CREATED and PROFILE_DELETED audit events carry the correct profile_id
"""

import pytest

from accounts.models import User
from audit.models import AuditAction, AuditEvent
from profiles.models import HealthProfile

pytestmark = pytest.mark.django_db

ME_URL = "/api/profiles/me"
DEMOGRAPHICS_URL = "/api/profiles/me/demographics"
WELLNESS_URL = "/api/profiles/me/wellness"
CONTACTS_URL = "/api/profiles/me/emergency-contacts"

PASSWORD = "Str0ng!Pass#2026"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_bare_user(email, full_name):
    """Create a user WITHOUT a profile (unlike the conftest fixture)."""
    return User.objects.create_user(email=email, password=PASSWORD, full_name=full_name)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bare_client(api_client, db):
    """A logged-in member whose account has NO profile yet."""
    u = _create_bare_user("lifecycle@example.com", "Lifecycle Demo")
    token = api_client.get("/api/auth/csrf").json()["csrfToken"]
    resp = api_client.post(
        "/api/auth/user/login",
        {"email": "lifecycle@example.com", "password": PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert resp.status_code == 200, resp.json()
    return api_client, u


# ---------------------------------------------------------------------------
# 1. Profile creation – basic
# ---------------------------------------------------------------------------


def test_create_profile_returns_201(bare_client):
    client, _ = bare_client
    response = client.post(ME_URL, {}, format="json")
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "ACTIVE"
    assert data["completion"]["percent"] == 0


def test_create_profile_emits_audit_event(bare_client):
    client, user = bare_client
    response = client.post(ME_URL, {}, format="json")
    assert response.status_code == 201
    profile_id = response.json()["id"]
    event = AuditEvent.objects.filter(
        action=AuditAction.PROFILE_CREATED,
        profile_id=profile_id,
    ).first()
    assert event is not None, "PROFILE_CREATED audit event not found"
    assert event.profile_id == profile_id


def test_create_profile_owner_is_authenticated_user(bare_client):
    """Any owner field in the request body must be ignored."""
    client, user = bare_client
    # Attempt to inject a different owner – the server must use authenticated user.
    response = client.post(ME_URL, {"user": 99999, "user_id": 99999}, format="json")
    assert response.status_code == 201
    profile = HealthProfile.objects.get(user=user)
    assert profile.user == user


def test_get_after_create_returns_200(bare_client):
    client, _ = bare_client
    client.post(ME_URL, {}, format="json")
    response = client.get(ME_URL)
    assert response.status_code == 200


def test_create_initialises_demographics_and_wellness(bare_client):
    """Sections must exist after creation (empty but present)."""
    client, user = bare_client
    client.post(ME_URL, {}, format="json")
    profile = HealthProfile.objects.select_related("demographics", "wellness").get(user=user)
    assert hasattr(profile, "demographics")
    assert hasattr(profile, "wellness")


# ---------------------------------------------------------------------------
# 2. Duplicate creation → 409
# ---------------------------------------------------------------------------


def test_duplicate_creation_returns_409(bare_client):
    client, _ = bare_client
    first = client.post(ME_URL, {}, format="json")
    assert first.status_code == 201
    second = client.post(ME_URL, {}, format="json")
    assert second.status_code == 409
    assert "already exists" in second.json().get("detail", "").lower()


def test_duplicate_creation_does_not_create_extra_profile(bare_client):
    client, user = bare_client
    client.post(ME_URL, {}, format="json")
    client.post(ME_URL, {}, format="json")
    assert HealthProfile.objects.filter(user=user).count() == 1


# ---------------------------------------------------------------------------
# 3. GET without profile → 404 (no auto-creation)
# ---------------------------------------------------------------------------


def test_get_without_profile_returns_404(bare_client):
    client, _ = bare_client
    response = client.get(ME_URL)
    assert response.status_code == 404


def test_get_does_not_auto_create_profile(bare_client):
    client, user = bare_client
    client.get(ME_URL)  # Should be 404, not create a profile
    assert HealthProfile.objects.filter(user=user).count() == 0


# ---------------------------------------------------------------------------
# 4. Root PATCH → 405
# ---------------------------------------------------------------------------


def test_root_patch_returns_405(bare_client):
    client, _ = bare_client
    # Even before a profile exists, PATCH /me must return 405 (method not allowed)
    response = client.patch(ME_URL, {"status": "INACTIVE"}, format="json")
    assert response.status_code == 405


def test_root_patch_does_not_change_profile(user, login, api_client):
    """With an existing profile, PATCH /me still returns 405 and changes nothing."""
    login(api_client)
    original = HealthProfile.objects.get(user=user).status
    api_client.patch(ME_URL, {"status": "INACTIVE"}, format="json")
    assert HealthProfile.objects.get(user=user).status == original


# ---------------------------------------------------------------------------
# 5. Profile deletion
# ---------------------------------------------------------------------------


def test_delete_profile_returns_204(user, login, api_client):
    login(api_client)
    response = api_client.delete(ME_URL)
    assert response.status_code == 204


def test_delete_profile_removes_it(user, login, api_client):
    login(api_client)
    api_client.delete(ME_URL)
    assert HealthProfile.objects.filter(user=user).count() == 0


def test_delete_profile_preserves_user_account(user, login, api_client):
    login(api_client)
    api_client.delete(ME_URL)
    assert User.objects.filter(pk=user.pk).exists()


def test_get_after_delete_returns_404(user, login, api_client):
    login(api_client)
    api_client.delete(ME_URL)
    response = api_client.get(ME_URL)
    assert response.status_code == 404


def test_delete_emits_audit_event_with_correct_profile_id(user, login, api_client):
    login(api_client)
    profile_id = HealthProfile.objects.get(user=user).pk
    api_client.delete(ME_URL)
    event = AuditEvent.objects.filter(
        action=AuditAction.PROFILE_DELETED,
        profile_id=profile_id,
    ).first()
    assert event is not None, "PROFILE_DELETED audit event not found"
    assert event.profile_id == profile_id


def test_delete_without_profile_returns_404(bare_client):
    client, _ = bare_client
    response = client.delete(ME_URL)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 6. Audit history survives deletion
# ---------------------------------------------------------------------------


def test_audit_history_survives_profile_deletion(user, login, api_client):
    """
    After deleting the profile, all previous audit events for that profile_id
    must still be retrievable (because AuditEvent.profile_id is a plain
    BigIntegerField, not a FK that cascades).
    """
    login(api_client)
    # Create a demographics update to build some audit history.
    api_client.patch(
        DEMOGRAPHICS_URL,
        {"country": "Canada"},
        format="json",
    )
    profile_id = HealthProfile.objects.get(user=user).pk
    pre_delete_count = AuditEvent.objects.filter(profile_id=profile_id).count()
    assert pre_delete_count >= 1

    api_client.delete(ME_URL)

    # All prior events still exist, plus the deletion event itself.
    post_delete_count = AuditEvent.objects.filter(profile_id=profile_id).count()
    assert post_delete_count == pre_delete_count + 1  # +1 for PROFILE_DELETED
    # The deleted-profile's row no longer exists in health_profiles.
    assert HealthProfile.objects.filter(pk=profile_id).count() == 0


# ---------------------------------------------------------------------------
# 7. Full lifecycle sequence (steps 1–10 from the spec)
# ---------------------------------------------------------------------------


def test_full_lifecycle_sequence(bare_client):
    """
    1. Create a profile.
    2. Read the profile.
    3. Edit supported profile information.
    4. Delete the root profile.
    5. Verify that the profile is gone.
    6. Verify that the account remains.
    7. Verify that the deletion audit event retains the original profile ID.
    8. Re-create the profile.
    9. Verify that the new profile has a different identifier.
    10. Verify that the old audit history remains intact.
    """
    client, user = bare_client

    # Step 1: Create
    create_resp = client.post(ME_URL, {}, format="json")
    assert create_resp.status_code == 201
    profile_id_v1 = create_resp.json()["id"]

    # Step 2: Read
    get_resp = client.get(ME_URL)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == profile_id_v1

    # Step 3: Edit demographics
    patch_resp = client.patch(
        DEMOGRAPHICS_URL,
        {"country": "Canada", "date_of_birth": "1990-06-15", "gender": "FEMALE"},
        format="json",
    )
    assert patch_resp.status_code == 200

    # Step 4: Delete
    delete_resp = client.delete(ME_URL)
    assert delete_resp.status_code == 204

    # Step 5: Profile is gone
    assert client.get(ME_URL).status_code == 404
    assert HealthProfile.objects.filter(pk=profile_id_v1).count() == 0

    # Step 6: Account remains
    assert User.objects.filter(pk=user.pk).exists()

    # Step 7: Deletion audit event retains original profile_id
    deletion_event = AuditEvent.objects.filter(
        action=AuditAction.PROFILE_DELETED,
        profile_id=profile_id_v1,
    ).first()
    assert deletion_event is not None
    assert deletion_event.profile_id == profile_id_v1

    # All history for v1 is still there (creation + demographics + deletion).
    assert AuditEvent.objects.filter(profile_id=profile_id_v1).count() >= 3

    # Step 8: Re-create
    recreate_resp = client.post(ME_URL, {}, format="json")
    assert recreate_resp.status_code == 201
    profile_id_v2 = recreate_resp.json()["id"]

    # Step 9: New profile has a different identifier
    assert profile_id_v2 != profile_id_v1

    # Step 10: Old audit history remains intact
    old_history = AuditEvent.objects.filter(profile_id=profile_id_v1)
    assert old_history.count() >= 3
    actions = set(old_history.values_list("action", flat=True))
    assert AuditAction.PROFILE_CREATED in actions
    assert AuditAction.PROFILE_DELETED in actions


# ---------------------------------------------------------------------------
# 8. Cross-user and role denial
# ---------------------------------------------------------------------------


def test_admin_cannot_create_member_profile(api_client, admin, admin_login):
    admin_login(api_client)
    response = api_client.post(ME_URL, {}, format="json")
    # Admin session is rejected by CookieJWTAuthentication on member endpoints.
    assert response.status_code == 401


def test_admin_cannot_delete_member_profile(api_client, admin, admin_login):
    admin_login(api_client)
    response = api_client.delete(ME_URL)
    assert response.status_code == 401


def test_anonymous_cannot_create_profile(api_client):
    response = api_client.post(ME_URL, {}, format="json")
    assert response.status_code == 401


def test_anonymous_cannot_delete_profile(api_client):
    response = api_client.delete(ME_URL)
    assert response.status_code == 401


def test_member_can_only_delete_own_profile(api_client, user, other_user, login):
    """
    There is only one DELETE /api/profiles/me endpoint, which always
    targets the authenticated user's own profile.  A member cannot reach
    another member's profile by this route.
    """
    login(api_client, email="sara@example.com")
    # Delete sara's profile.
    response = api_client.delete(ME_URL)
    assert response.status_code == 204
    # Omar's profile must be untouched.
    assert HealthProfile.objects.filter(user=other_user).exists()


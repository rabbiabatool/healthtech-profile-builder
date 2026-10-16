import pytest

from profiles.models import HealthProfile

pytestmark = pytest.mark.django_db

ME_URL = "/api/profiles/me"


def test_user_can_view_own_profile(api_client, user, login):
    login(api_client)
    response = api_client.get(ME_URL)
    assert response.status_code == 200
    assert response.json()["email"] == "sara@example.com"
    assert response.json()["status"] == "ACTIVE"


def test_user_can_update_own_profile(api_client, user, login):
    login(api_client)
    payload = {
        "blood_group": "O+",
        "height_cm": "172.5",
        "weight_kg": "64.0",
        "date_of_birth": "1995-04-12",
        "allergies": "Fictional pollen sensitivity",
        "emergency_contact": "Fictional Contact 555-0100",
    }
    response = api_client.patch(ME_URL, payload, format="json")
    assert response.status_code == 200

    profile = HealthProfile.objects.get(user=user)
    assert profile.blood_group == "O+"
    assert str(profile.height_cm) == "172.5"
    assert profile.allergies == "Fictional pollen sensitivity"


def test_unauthenticated_access_is_rejected(api_client):
    assert api_client.get(ME_URL).status_code == 401
    assert api_client.patch(ME_URL, {"allergies": "x"}, format="json").status_code == 401


def test_user_only_sees_their_own_profile(api_client, user, other_user, login):
    HealthProfile.objects.filter(user=other_user).update(allergies="Fictional secret of Omar")
    login(api_client)
    response = api_client.get(ME_URL)
    assert response.json()["email"] == "sara@example.com"
    assert "Fictional secret of Omar" not in response.content.decode()


def test_patch_never_touches_another_users_profile(api_client, user, other_user, login):
    other_profile = HealthProfile.objects.get(user=other_user)
    login(api_client)
    api_client.patch(
        ME_URL,
        {"allergies": "changed", "user": other_user.id, "id": other_profile.id},
        format="json",
    )
    other_profile.refresh_from_db()
    assert other_profile.allergies == ""
    assert HealthProfile.objects.get(user=user).allergies == "changed"


def test_user_cannot_change_their_own_status(api_client, user, login):
    login(api_client)
    response = api_client.patch(ME_URL, {"status": "INACTIVE"}, format="json")
    assert response.status_code == 200
    assert HealthProfile.objects.get(user=user).status == "ACTIVE"


def test_other_users_profile_has_no_url(api_client, user, other_user, login):
    other_profile = HealthProfile.objects.get(user=other_user)
    login(api_client)
    assert api_client.get(f"/api/profiles/{other_profile.id}").status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"height_cm": "-5"},
        {"height_cm": "0"},
        {"height_cm": "500"},
        {"weight_kg": "-1"},
        {"weight_kg": "9999"},
        {"date_of_birth": "2999-01-01"},
        {"date_of_birth": "1800-01-01"},
        {"date_of_birth": "not-a-date"},
        {"blood_group": "Z+"},
    ],
)
def test_profile_update_rejects_invalid_input(api_client, user, login, payload):
    login(api_client)
    response = api_client.patch(ME_URL, payload, format="json")
    assert response.status_code == 400


def test_admin_session_cannot_use_user_endpoints(api_client, admin):
    api_client.force_login(admin)
    assert api_client.get(ME_URL).status_code == 401


def test_deactivated_profile_can_be_read_but_not_edited(api_client, user, login):
    login(api_client)
    HealthProfile.objects.filter(user=user).update(status="INACTIVE")
    assert api_client.get(ME_URL).status_code == 200
    assert api_client.patch(ME_URL, {"allergies": "x"}, format="json").status_code == 403


def test_patch_requires_csrf_token_in_browser_mode(csrf_client, user, login, csrf_header):
    login(csrf_client)
    payload = {"allergies": "Fictional pollen sensitivity"}
    assert csrf_client.patch(ME_URL, payload, format="json").status_code == 403

    response = csrf_client.patch(ME_URL, payload, format="json", **csrf_header(csrf_client))
    assert response.status_code == 200
import pytest

from profiles.models import HealthProfile, WellnessPreferences
from profiles.services import recalculate_completion

pytestmark = pytest.mark.django_db

ME_URL = "/api/profiles/me"

FORBIDDEN_KEYS = {"password", "is_staff", "is_superuser", "last_login", "role", "token", "access", "refresh"}


def collect_keys(value):
    keys = set()
    if isinstance(value, dict):
        for key, inner in value.items():
            keys.add(key)
            keys |= collect_keys(inner)
    elif isinstance(value, list):
        for item in value:
            keys |= collect_keys(item)
    return keys


def test_user_can_view_own_profile(api_client, user, login):
    login(api_client)
    response = api_client.get(ME_URL)
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {
        "id",
        "full_name",
        "email",
        "status",
        "completion",
        "demographics",
        "emergency_contacts",
        "wellness",
        "created_at",
        "updated_at",
    }
    assert data["email"] == "sara@example.com"
    assert data["status"] == "ACTIVE"
    assert data["emergency_contacts"] == []


def test_new_profile_reports_every_item_as_missing(api_client, user, login):
    login(api_client)
    completion = api_client.get(ME_URL).json()["completion"]
    assert completion["percent"] == 0
    assert completion["status"] == "NOT_STARTED"
    assert len(completion["missing"]) == 10
    assert completion["missing"][0] == {"key": "date_of_birth", "label": "Date of birth"}


def test_completion_in_the_response_tracks_the_sections(api_client, user, login):
    profile = HealthProfile.objects.get(user=user)
    WellnessPreferences.objects.filter(profile=profile).update(
        activity_level="MODERATE",
        diet_preference="NO_PREFERENCE",
        reminder_channel="EMAIL",
    )
    recalculate_completion(profile)

    login(api_client)
    completion = api_client.get(ME_URL).json()["completion"]
    assert completion["percent"] == 30
    assert completion["status"] == "IN_PROGRESS"
    assert "activity_level" not in [item["key"] for item in completion["missing"]]


def test_unauthenticated_access_is_rejected(api_client):
    assert api_client.get(ME_URL).status_code == 401


def test_the_whole_profile_cannot_be_patched(api_client, user, login):
    login(api_client)
    assert api_client.patch(ME_URL, {"status": "INACTIVE"}, format="json").status_code == 405
    assert HealthProfile.objects.get(user=user).status == "ACTIVE"


def test_user_only_sees_their_own_data(api_client, user, other_user, login):
    WellnessPreferences.objects.filter(profile__user=other_user).update(allergy_notes="Fictional secret of Omar")
    login(api_client)
    response = api_client.get(ME_URL)
    assert response.json()["email"] == "sara@example.com"
    assert "Fictional secret of Omar" not in response.content.decode()


def test_other_users_profile_has_no_url(api_client, user, other_user, login):
    other_profile = HealthProfile.objects.get(user=other_user)
    login(api_client)
    assert api_client.get(f"/api/profiles/{other_profile.id}").status_code == 404


def test_response_has_no_sensitive_keys(api_client, user, login):
    login(api_client)
    keys = collect_keys(api_client.get(ME_URL).json())
    assert keys & FORBIDDEN_KEYS == set()


def test_deactivated_profile_can_still_be_read(api_client, user, login):
    login(api_client)
    HealthProfile.objects.filter(user=user).update(status="INACTIVE")
    response = api_client.get(ME_URL)
    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"


def test_admin_session_cannot_use_the_member_profile(api_client, admin, admin_login):
    admin_login(api_client)
    assert api_client.get(ME_URL).status_code == 401
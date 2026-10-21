import json

import pytest
from django.contrib.auth.hashers import make_password

from accounts.models import User
from audit.models import AuditEvent
from profiles.models import HealthProfile
from profiles.services import create_profile_with_sections

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng!Pass#2026"
UNUSED_HASH = make_password("Unused!Pass#123")
LIST_URL = "/api/admin/profiles"


def make_member(email, full_name):
    user = User.objects.create(email=email, password=UNUSED_HASH, full_name=full_name)
    return create_profile_with_sections(user)


def dump_events():
    return json.dumps(list(AuditEvent.objects.values()), default=str)


def events(action):
    return AuditEvent.objects.filter(action=action)


def test_admin_login_is_recorded(api_client, admin, admin_login):
    assert admin_login(api_client).status_code == 200
    event = events("ADMIN_LOGIN").get()
    assert event.actor_id == admin.id
    assert event.actor_role == "ADMIN"
    assert event.outcome == "SUCCESS"
    assert event.profile_id is None
    assert event.metadata == {}


def test_a_failed_admin_login_is_recorded_without_the_attempted_email(api_client, admin, admin_login):
    assert admin_login(api_client, password="Wrong!Pass#999").status_code == 401
    event = events("ADMIN_LOGIN_FAILED").get()
    assert event.actor_id is None
    assert event.actor_role == "ANONYMOUS"
    assert event.outcome == "FAILED"
    assert "boss@example.com" not in dump_events()
    assert "Wrong!Pass#999" not in dump_events()


def test_a_members_valid_credentials_count_as_a_failed_admin_login(api_client, user, admin_login):
    assert admin_login(api_client, email="sara@example.com").status_code == 401
    assert events("ADMIN_LOGIN_FAILED").count() == 1
    assert events("ADMIN_LOGIN").count() == 0


def test_admin_logout_is_recorded(admin_client, admin):
    assert admin_client.post("/api/admin/logout").status_code == 204
    event = events("ADMIN_LOGOUT").get()
    assert event.actor_id == admin.id


def test_viewing_a_profile_is_recorded(admin_client, admin, user):
    profile = HealthProfile.objects.get(user=user)
    assert admin_client.get(f"{LIST_URL}/{profile.pk}").status_code == 200
    event = events("ADMIN_PROFILE_VIEWED").get()
    assert (event.actor_id, event.profile_id) == (admin.id, profile.pk)


def test_viewing_an_unknown_profile_records_nothing(admin_client):
    assert admin_client.get(f"{LIST_URL}/999999").status_code == 404
    assert events("ADMIN_PROFILE_VIEWED").count() == 0


def test_a_search_is_recorded_without_the_search_term(admin_client):
    make_member("sara.find@example.com", "Sara Findme")
    response = admin_client.get(LIST_URL, {"search": "findme"})
    assert response.json()["count"] == 1
    event = events("ADMIN_SEARCH_PERFORMED").get()
    assert event.metadata == {"filters_used": ["search"], "result_count": 1}
    assert event.profile_id is None
    assert "findme" not in dump_events().lower()


@pytest.mark.parametrize("params", [{}, {"ordering": "completion_percent"}, {"page_size": 5}])
def test_plain_browsing_records_nothing(admin_client, params):
    assert admin_client.get(LIST_URL, params).status_code == 200
    assert events("ADMIN_SEARCH_PERFORMED").count() == 0


def test_only_the_first_page_of_a_filtered_list_is_recorded(admin_client):
    users = User.objects.bulk_create(
        [User(email=f"member{i}@example.com", password=UNUSED_HASH, full_name=f"Member {i}") for i in range(25)]
    )
    HealthProfile.objects.bulk_create([HealthProfile(user=user) for user in users])

    assert admin_client.get(LIST_URL, {"status": "ACTIVE"}).status_code == 200
    assert admin_client.get(LIST_URL, {"status": "ACTIVE", "page": 2}).status_code == 200
    assert events("ADMIN_SEARCH_PERFORMED").count() == 1


def test_deactivation_is_recorded(admin_client, admin, user):
    profile = HealthProfile.objects.get(user=user)
    assert admin_client.patch(f"{LIST_URL}/{profile.pk}/deactivate").status_code == 200
    event = events("ADMIN_PROFILE_DEACTIVATED").get()
    assert (event.actor_id, event.profile_id) == (admin.id, profile.pk)
    assert event.metadata == {"from_status": "ACTIVE", "to_status": "INACTIVE"}


def test_repeating_a_deactivation_records_nothing_new(admin_client, user):
    profile = HealthProfile.objects.get(user=user)
    admin_client.patch(f"{LIST_URL}/{profile.pk}/deactivate")
    admin_client.patch(f"{LIST_URL}/{profile.pk}/deactivate")
    assert events("ADMIN_PROFILE_DEACTIVATED").count() == 1


def test_reactivation_is_recorded(admin_client, user):
    profile = HealthProfile.objects.get(user=user)
    HealthProfile.objects.filter(pk=profile.pk).update(status="INACTIVE")
    assert admin_client.patch(f"{LIST_URL}/{profile.pk}/reactivate").status_code == 200
    event = events("ADMIN_PROFILE_REACTIVATED").get()
    assert event.metadata == {"from_status": "INACTIVE", "to_status": "ACTIVE"}


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/api/admin/profiles/{id}"),
        ("patch", "/api/admin/profiles/{id}/deactivate"),
        ("get", "/api/admin/profiles?search=sara"),
        ("get", "/api/admin/audit-events"),
    ],
)
def test_denied_requests_record_nothing(api_client, user, login, method, path):
    profile = HealthProfile.objects.get(user=user)
    login(api_client)
    response = getattr(api_client, method)(path.format(id=profile.pk))
    assert response.status_code == 401
    assert AuditEvent.objects.count() == 0


def test_admin_activity_leaves_no_secrets_in_the_log(api_client, admin, user, admin_login):
    admin_login(api_client)
    make_member("sara.find@example.com", "Sara Findme")
    api_client.get(LIST_URL, {"search": "findme"})
    profile = HealthProfile.objects.get(user=user)
    api_client.get(f"{LIST_URL}/{profile.pk}")
    api_client.patch(f"{LIST_URL}/{profile.pk}/deactivate")
    api_client.post("/api/admin/logout")

    stored = dump_events().lower()
    assert "@" not in stored
    for secret in (PASSWORD.lower(), "admin_session", "csrf", "token", "findme"):
        assert secret not in stored
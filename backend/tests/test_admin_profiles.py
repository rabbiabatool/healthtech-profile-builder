from datetime import timedelta

import pytest
from django.contrib.auth.hashers import make_password
from django.db import connection
from django.utils import timezone

from accounts.models import User
from profiles.models import HealthProfile, ProfileStatus

pytestmark = pytest.mark.django_db

LIST_URL = "/api/admin/profiles"
UNUSED_HASH = make_password("Unused!Pass#123")


def make_member(email, full_name, status=ProfileStatus.ACTIVE):
    user = User.objects.create(email=email, password=UNUSED_HASH, full_name=full_name)
    return HealthProfile.objects.create(user=user, status=status)


def make_many_members(count):
    users = User.objects.bulk_create(
        [
            User(email=f"member{i}@example.com", password=UNUSED_HASH, full_name=f"Member {i}")
            for i in range(count)
        ]
    )
    HealthProfile.objects.bulk_create([HealthProfile(user=user) for user in users])


def test_list_is_newest_first(admin_client):
    old = make_member("old@example.com", "Old Member")
    make_member("new@example.com", "New Member")
    HealthProfile.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=30))

    response = admin_client.get(LIST_URL)
    assert response.status_code == 200
    emails = [row["email"] for row in response.json()["results"]]
    assert emails == ["new@example.com", "old@example.com"]


def test_list_requires_an_admin_session(api_client):
    assert api_client.get(LIST_URL).status_code == 401


@pytest.mark.parametrize("status, expected", [("ACTIVE", 2), ("active", 2), ("INACTIVE", 1)])
def test_list_can_filter_by_status(admin_client, status, expected):
    make_member("a@example.com", "Alpha")
    make_member("b@example.com", "Bravo")
    make_member("c@example.com", "Charlie", status=ProfileStatus.INACTIVE)

    response = admin_client.get(LIST_URL, {"status": status})
    assert response.status_code == 200
    assert response.json()["count"] == expected


def test_list_rejects_an_invalid_status(admin_client):
    response = admin_client.get(LIST_URL, {"status": "DELETED"})
    assert response.status_code == 400
    assert "status" in response.json()


def test_search_matches_name_ignoring_case(admin_client):
    make_member("sara.find@example.com", "Sara Findme")
    make_member("omar@example.com", "Omar Other")

    response = admin_client.get(LIST_URL, {"search": "FINDME"})
    assert [row["email"] for row in response.json()["results"]] == ["sara.find@example.com"]


def test_search_matches_email(admin_client):
    make_member("sara.find@example.com", "Sara Findme")
    make_member("omar@example.com", "Omar Other")

    response = admin_client.get(LIST_URL, {"search": "omar@"})
    assert [row["email"] for row in response.json()["results"]] == ["omar@example.com"]


def test_search_with_no_match_returns_empty_list(admin_client):
    make_member("sara@example.com", "Sara Demo")
    response = admin_client.get(LIST_URL, {"search": "zzzzzz"})
    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["results"] == []


def test_list_is_paginated(admin_client):
    make_many_members(25)

    first = admin_client.get(LIST_URL).json()
    assert first["count"] == 25
    assert len(first["results"]) == 20
    assert first["next"] is not None

    second = admin_client.get(LIST_URL, {"page": 2}).json()
    assert len(second["results"]) == 5
    first_ids = {row["id"] for row in first["results"]}
    second_ids = {row["id"] for row in second["results"]}
    assert first_ids.isdisjoint(second_ids)


def test_page_size_can_be_chosen(admin_client):
    make_many_members(12)
    response = admin_client.get(LIST_URL, {"page_size": 5})
    assert len(response.json()["results"]) == 5


def test_list_never_exposes_passwords(admin_client):
    make_member("sara@example.com", "Sara Demo")
    body = admin_client.get(LIST_URL).content.decode()
    assert "password" not in body
    assert UNUSED_HASH not in body


def test_admin_can_view_profile_details(admin_client):
    profile = make_member("sara@example.com", "Sara Demo")
    HealthProfile.objects.filter(pk=profile.pk).update(allergies="Fictional pollen sensitivity")

    response = admin_client.get(f"{LIST_URL}/{profile.pk}")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "sara@example.com"
    assert data["user_id"] == profile.user_id
    assert data["allergies"] == "Fictional pollen sensitivity"


def test_unknown_profile_returns_404(admin_client):
    assert admin_client.get(f"{LIST_URL}/999999").status_code == 404


def test_admin_can_deactivate_a_profile(admin_client):
    profile = make_member("sara@example.com", "Sara Demo")
    response = admin_client.patch(f"{LIST_URL}/{profile.pk}/deactivate")
    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"
    profile.refresh_from_db()
    assert profile.status == ProfileStatus.INACTIVE


def test_deactivating_twice_is_safe(admin_client):
    profile = make_member("sara@example.com", "Sara Demo", status=ProfileStatus.INACTIVE)
    response = admin_client.patch(f"{LIST_URL}/{profile.pk}/deactivate")
    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"


def test_admin_can_reactivate_a_profile(admin_client):
    profile = make_member("sara@example.com", "Sara Demo", status=ProfileStatus.INACTIVE)
    response = admin_client.patch(f"{LIST_URL}/{profile.pk}/reactivate")
    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"


def test_deactivate_requires_csrf_token_in_browser_mode(
    csrf_client, admin, user, admin_login, csrf_header
):
    admin_login(csrf_client)
    profile = HealthProfile.objects.get(user=user)
    url = f"{LIST_URL}/{profile.pk}/deactivate"

    assert csrf_client.patch(url).status_code == 403
    assert HealthProfile.objects.get(user=user).status == ProfileStatus.ACTIVE

    assert csrf_client.patch(url, **csrf_header(csrf_client)).status_code == 200
    assert HealthProfile.objects.get(user=user).status == ProfileStatus.INACTIVE


def test_deactivated_profile_blocks_user_edits(api_client, admin_client, user, login):
    login(api_client)
    profile = HealthProfile.objects.get(user=user)

    assert admin_client.patch(f"{LIST_URL}/{profile.pk}/deactivate").status_code == 200
    response = api_client.patch("/api/profiles/me", {"allergies": "x"}, format="json")
    assert response.status_code == 403


def test_status_created_composite_index_exists():
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, "health_profiles")
    index = constraints["idx_profile_status_created_id"]
    assert index["index"] is True
    assert index["columns"] == ["status", "created_at", "id"]
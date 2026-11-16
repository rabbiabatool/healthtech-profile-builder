from datetime import timedelta

import pytest
from django.utils import timezone

from audit.models import AuditAction, AuditEvent

pytestmark = pytest.mark.django_db

FEED_URL = "/api/admin/audit-events"
TIMELINE_URL = "/api/admin/profiles/{profile_id}/audit-events"


def add_events(count, **overrides):
    values = {
        "actor_role": "USER",
        "action": AuditAction.DEMOGRAPHICS_UPDATED,
        "profile_id": 1,
        "changed_fields": ["country"],
        "metadata": {"section": "demographics"},
    }
    values.update(overrides)
    AuditEvent.objects.bulk_create([AuditEvent(**values) for _ in range(count)])


def test_the_feed_requires_an_admin_session(api_client):
    assert api_client.get(FEED_URL).status_code == 401


def test_feed_rows_have_exactly_the_expected_keys(admin_client):
    rows = admin_client.get(FEED_URL).json()["results"]
    assert rows
    assert set(rows[0]) == {
        "id",
        "created_at",
        "actor_id",
        "actor_role",
        "action",
        "outcome",
        "profile_id",
        "changed_fields",
        "metadata",
    }


def test_the_feed_is_newest_first(admin_client):
    add_events(5)
    ids = [row["id"] for row in admin_client.get(FEED_URL).json()["results"]]
    assert ids == sorted(ids, reverse=True)


def test_cursor_pagination_walks_through_every_event_exactly_once(admin_client):
    add_events(45)
    seen = []
    url = FEED_URL
    while url:
        data = admin_client.get(url).json()
        assert "count" not in data
        seen.extend(row["id"] for row in data["results"])
        url = data["next"]
    assert len(seen) == len(set(seen)) == AuditEvent.objects.count()


def test_the_page_size_can_be_chosen(admin_client):
    add_events(10)
    assert len(admin_client.get(FEED_URL, {"page_size": 5}).json()["results"]) == 5


def test_the_feed_can_filter_by_action(admin_client):
    add_events(3)
    add_events(2, actor_role="ADMIN", action="ADMIN_LOGOUT")
    rows = admin_client.get(FEED_URL, {"action": "ADMIN_LOGOUT"}).json()["results"]
    assert len(rows) == 2
    assert {row["action"] for row in rows} == {"ADMIN_LOGOUT"}


def test_the_feed_can_filter_by_profile(admin_client):
    add_events(2, profile_id=7)
    add_events(3, profile_id=8)
    rows = admin_client.get(FEED_URL, {"profile_id": 7}).json()["results"]
    assert len(rows) == 2


def test_the_feed_can_filter_by_actor(admin_client, user):
    add_events(2, actor_id=user.id)
    add_events(3)
    rows = admin_client.get(FEED_URL, {"actor_id": user.id}).json()["results"]
    assert len(rows) == 2


def test_the_feed_can_filter_by_outcome(admin_client):
    add_events(2, outcome="FAILED", actor_role="ANONYMOUS", action="ADMIN_LOGIN_FAILED")
    rows = admin_client.get(FEED_URL, {"outcome": "FAILED"}).json()["results"]
    assert len(rows) == 2


def test_the_feed_can_filter_by_date(admin_client):
    add_events(3)
    tomorrow = (timezone.now() + timedelta(days=1)).date().isoformat()
    assert admin_client.get(FEED_URL, {"created_after": tomorrow}).json()["results"] == []
    assert admin_client.get(FEED_URL, {"created_before": tomorrow}).json()["results"]


@pytest.mark.parametrize(
    "params",
    [
        {"action": "HACK"},
        {"outcome": "MAYBE"},
        {"actor_id": "abc"},
        {"profile_id": "0"},
        {"created_after": "not-a-date"},
    ],
)
def test_invalid_filter_values_are_rejected(admin_client, params):
    assert admin_client.get(FEED_URL, params).status_code == 400


def test_the_profile_timeline_only_shows_that_profiles_events(admin_client):
    add_events(3, profile_id=11)
    add_events(2, profile_id=12)
    rows = admin_client.get(TIMELINE_URL.format(profile_id=11)).json()["results"]
    assert len(rows) == 3
    assert {row["profile_id"] for row in rows} == {11}
    ids = [row["id"] for row in rows]
    assert ids == sorted(ids, reverse=True)


def test_a_profile_without_events_has_an_empty_timeline(admin_client):
    response = admin_client.get(TIMELINE_URL.format(profile_id=999999))
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_reading_the_audit_log_is_not_itself_recorded(admin_client):
    before = AuditEvent.objects.count()
    admin_client.get(FEED_URL)
    admin_client.get(TIMELINE_URL.format(profile_id=1))
    assert AuditEvent.objects.count() == before


@pytest.mark.parametrize("url", [FEED_URL, TIMELINE_URL.format(profile_id=1)])
@pytest.mark.parametrize("method", ["post", "patch", "put", "delete"])
def test_the_audit_log_has_no_write_routes(admin_client, method, url):
    send = getattr(admin_client, method)
    response = send(url) if method == "delete" else send(url, {}, format="json")
    assert response.status_code == 405

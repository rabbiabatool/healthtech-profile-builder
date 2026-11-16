import pytest

from audit.models import AuditAction, AuditEvent
from audit.services import record_event

pytestmark = pytest.mark.django_db


def test_a_member_event_records_the_actor_and_role(user):
    event = record_event(user, AuditAction.DEMOGRAPHICS_UPDATED, profile_id=1, changed_fields=["country"])
    assert event.actor_id == user.id
    assert event.actor_role == "USER"


def test_an_admin_event_records_the_admin_role(admin):
    event = record_event(admin, AuditAction.ADMIN_LOGOUT)
    assert event.actor_id == admin.id
    assert event.actor_role == "ADMIN"


def test_no_actor_means_anonymous():
    event = record_event(None, AuditAction.ADMIN_LOGIN_FAILED, outcome="FAILED")
    assert event.actor_id is None
    assert event.actor_role == "ANONYMOUS"
    assert event.outcome == "FAILED"


def test_an_unknown_action_is_rejected(user):
    with pytest.raises(ValueError):
        record_event(user, "DELETE_EVERYTHING")


@pytest.mark.parametrize("names", [["password"], ["555-0142"], ["Fictional Contact"], [""]])
def test_only_known_field_names_are_accepted(user, names):
    with pytest.raises(ValueError):
        record_event(user, AuditAction.DEMOGRAPHICS_UPDATED, changed_fields=names)


@pytest.mark.parametrize("fields", ["country", {"country": "Canada"}, b"country"])
def test_changed_fields_must_be_a_list_of_names(user, fields):
    with pytest.raises(TypeError):
        record_event(user, AuditAction.DEMOGRAPHICS_UPDATED, changed_fields=fields)


@pytest.mark.parametrize(
    "metadata",
    [
        {"search_term": "sara"},
        {"email": "sara@example.com"},
        {"payload": {"phone": "555-0142"}},
        {"section": "passwords"},
        {"from_status": "DELETED"},
        {"filters_used": ["search", "phone"]},
        {"filters_used": "search"},
        {"result_count": -1},
        {"result_count": True},
        {"contact_id": 0},
    ],
)
def test_metadata_is_checked_against_the_allowlist(user, metadata):
    with pytest.raises(ValueError):
        record_event(user, AuditAction.ADMIN_SEARCH_PERFORMED, metadata=metadata)


def test_field_names_are_sorted_and_de_duplicated(user):
    event = record_event(
        user,
        AuditAction.DEMOGRAPHICS_UPDATED,
        changed_fields=["weight_kg", "country", "country"],
    )
    assert event.changed_fields == ["country", "weight_kg"]


def test_nothing_is_saved_when_validation_fails(user):
    with pytest.raises(ValueError):
        record_event(user, AuditAction.DEMOGRAPHICS_UPDATED, changed_fields=["password"])
    assert AuditEvent.objects.count() == 0


def test_error_messages_never_echo_the_rejected_value(user):
    with pytest.raises(ValueError) as error:
        record_event(user, AuditAction.DEMOGRAPHICS_UPDATED, changed_fields=["555-0142"])
    assert "555-0142" not in str(error.value)

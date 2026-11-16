import pytest
from django.db import IntegrityError, connection, transaction

from audit.models import AuditAction, AuditEvent, AuditImmutableError

pytestmark = pytest.mark.django_db


def make_event(**overrides):
    values = {
        "actor_role": "USER",
        "action": AuditAction.DEMOGRAPHICS_UPDATED,
        "profile_id": 1,
        "changed_fields": ["country"],
        "metadata": {"section": "demographics"},
    }
    values.update(overrides)
    return AuditEvent.objects.create(**values)


def test_an_event_can_be_recorded():
    event = make_event()
    assert event.pk is not None
    assert event.created_at is not None
    assert event.outcome == "SUCCESS"


def test_an_existing_event_cannot_be_changed():
    event = make_event()
    event.profile_id = 2
    with pytest.raises(AuditImmutableError):
        event.save()


def test_an_event_cannot_be_deleted():
    event = make_event()
    with pytest.raises(AuditImmutableError):
        event.delete()
    assert AuditEvent.objects.count() == 1


def test_bulk_updates_are_blocked():
    event = make_event()
    with pytest.raises(AuditImmutableError):
        AuditEvent.objects.filter(pk=event.pk).update(action="ADMIN_LOGOUT")


def test_bulk_deletes_are_blocked():
    make_event()
    with pytest.raises(AuditImmutableError):
        AuditEvent.objects.all().delete()
    assert AuditEvent.objects.count() == 1


def test_bulk_create_is_allowed():
    AuditEvent.objects.bulk_create(
        [AuditEvent(actor_role="ADMIN", action="ADMIN_LOGOUT") for _ in range(3)]
    )
    assert AuditEvent.objects.count() == 3


def test_events_survive_the_deletion_of_their_actor(user):
    event = make_event(actor=user)
    user.delete()
    event.refresh_from_db()
    assert event.actor_id is None
    assert AuditEvent.objects.count() == 1


@pytest.mark.parametrize(
    "values",
    [{"action": "HACK"}, {"actor_role": "ROOT"}, {"outcome": "MAYBE"}],
)
def test_the_database_rejects_invalid_values(values):
    with pytest.raises(IntegrityError), transaction.atomic():
        make_event(**values)


def test_the_planned_indexes_exist():
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, "audit_events")
    assert constraints["idx_audit_profile_newest"]["columns"] == ["profile_id", "id"]
    assert constraints["idx_audit_action_newest"]["columns"] == ["action", "id"]

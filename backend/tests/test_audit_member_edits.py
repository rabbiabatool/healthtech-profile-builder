import json

import pytest

from audit.models import AuditEvent
from profiles.models import Demographics, HealthProfile

pytestmark = pytest.mark.django_db

DEMOGRAPHICS_URL = "/api/profiles/me/demographics"
WELLNESS_URL = "/api/profiles/me/wellness"
CONTACTS_URL = "/api/profiles/me/emergency-contacts"
FEED_URL = "/api/admin/audit-events"

VALID_CONTACT = {"name": "Fictional Helper", "relationship": "FRIEND", "phone": "555-0101"}


def call(client, method, url, body=None):
    send = getattr(client, method)
    if method in ("post", "patch", "put"):
        return send(url, body if body is not None else {}, format="json")
    return send(url)


@pytest.fixture
def member(api_client, user, login):
    login(api_client)
    return api_client


def only_event():
    assert AuditEvent.objects.count() == 1
    return AuditEvent.objects.get()


def test_updating_demographics_records_one_event(member, user):
    assert call(member, "patch", DEMOGRAPHICS_URL, {"country": "Canada", "height_cm": "170.0"}).status_code == 200
    event = only_event()
    assert event.action == "DEMOGRAPHICS_UPDATED"
    assert event.actor_id == user.id
    assert event.actor_role == "USER"
    assert event.outcome == "SUCCESS"
    assert event.profile_id == HealthProfile.objects.get(user=user).pk
    assert event.changed_fields == ["country", "height_cm"]
    assert event.metadata == {"section": "demographics"}


def test_saving_the_same_values_again_records_nothing_new(member):
    call(member, "patch", DEMOGRAPHICS_URL, {"country": "Canada"})
    call(member, "patch", DEMOGRAPHICS_URL, {"country": "Canada"})
    assert AuditEvent.objects.count() == 1


def test_resetting_demographics_records_only_the_fields_that_changed(member):
    call(member, "patch", DEMOGRAPHICS_URL, {"country": "Canada", "preferred_language": "English"})
    assert member.delete(DEMOGRAPHICS_URL).status_code == 200
    reset = AuditEvent.objects.get(action="DEMOGRAPHICS_RESET")
    assert reset.changed_fields == ["country", "preferred_language"]


def test_wellness_updates_and_resets_are_recorded(member):
    call(member, "patch", WELLNESS_URL, {"activity_level": "LIGHT", "allergy_notes": "Fictional note"})
    assert member.delete(WELLNESS_URL).status_code == 200
    update = AuditEvent.objects.get(action="WELLNESS_UPDATED")
    reset = AuditEvent.objects.get(action="WELLNESS_RESET")
    assert update.changed_fields == ["activity_level", "allergy_notes"]
    assert reset.changed_fields == ["activity_level", "allergy_notes"]
    assert update.metadata == {"section": "wellness"}


def test_creating_a_contact_is_recorded(member):
    created = call(member, "post", CONTACTS_URL, VALID_CONTACT).json()
    event = only_event()
    assert event.action == "EMERGENCY_CONTACT_CREATED"
    assert event.changed_fields == ["is_primary", "name", "phone", "relationship"]
    assert event.metadata == {"section": "emergency_contacts", "contact_id": created["id"]}


def test_editing_a_contact_is_recorded_with_the_changed_names(member):
    created = call(member, "post", CONTACTS_URL, VALID_CONTACT).json()
    call(member, "patch", f"{CONTACTS_URL}/{created['id']}", {"name": "Renamed Helper", "phone": "555-0177"})
    event = AuditEvent.objects.get(action="EMERGENCY_CONTACT_UPDATED")
    assert event.changed_fields == ["name", "phone"]


def test_promoting_a_contact_is_recorded_as_a_primary_change(member):
    call(member, "post", CONTACTS_URL, VALID_CONTACT)
    second = call(member, "post", CONTACTS_URL, {**VALID_CONTACT, "name": "Second", "phone": "555-0102"}).json()
    call(member, "patch", f"{CONTACTS_URL}/{second['id']}", {"is_primary": True})
    event = AuditEvent.objects.get(action="EMERGENCY_CONTACT_UPDATED")
    assert event.changed_fields == ["is_primary"]


def test_deleting_a_contact_is_recorded_without_any_fields(member):
    created = call(member, "post", CONTACTS_URL, VALID_CONTACT).json()
    assert member.delete(f"{CONTACTS_URL}/{created['id']}").status_code == 204
    event = AuditEvent.objects.get(action="EMERGENCY_CONTACT_DELETED")
    assert event.changed_fields == []
    assert event.metadata == {"section": "emergency_contacts", "contact_id": created["id"]}


def test_a_rejected_edit_records_nothing(member):
    assert call(member, "patch", DEMOGRAPHICS_URL, {"height_cm": "-5"}).status_code == 400
    assert AuditEvent.objects.count() == 0


def test_touching_someone_elses_contact_records_nothing(api_client, user, other_user, login):
    from profiles.models import EmergencyContact

    victim = EmergencyContact.objects.create(
        profile=HealthProfile.objects.get(user=other_user), name="Victim", phone="555-0142", is_primary=True
    )
    login(api_client)
    assert call(api_client, "patch", f"{CONTACTS_URL}/{victim.id}", {"name": "Hacked"}).status_code == 404
    assert AuditEvent.objects.count() == 0


def test_a_blocked_write_on_a_deactivated_profile_records_nothing(member, user):
    HealthProfile.objects.filter(user=user).update(status="INACTIVE")
    assert call(member, "patch", DEMOGRAPHICS_URL, {"country": "Canada"}).status_code == 403
    assert AuditEvent.objects.count() == 0


def test_the_edit_is_rolled_back_if_the_audit_write_fails(member, user, monkeypatch):
    def broken_audit(*args, **kwargs):
        raise RuntimeError("audit store unavailable")

    monkeypatch.setattr("profiles.services.record_event", broken_audit)
    with pytest.raises(RuntimeError):
        call(member, "patch", DEMOGRAPHICS_URL, {"country": "Canada"})

    assert Demographics.objects.get(profile__user=user).country == ""
    assert AuditEvent.objects.count() == 0


MARKERS = [
    "Canada-MARKER",
    "MARKER-ALLERGY-7731",
    "Marker Contact Name",
    "555-0142",
    "marker.contact@example.com",
]


def test_audit_rows_never_contain_the_values_that_were_saved(member, admin_client):
    call(member, "patch", DEMOGRAPHICS_URL, {"country": "Canada-MARKER"})
    call(member, "patch", WELLNESS_URL, {"allergy_notes": "MARKER-ALLERGY-7731"})
    call(
        member,
        "post",
        CONTACTS_URL,
        {
            "name": "Marker Contact Name",
            "relationship": "FRIEND",
            "phone": "555-0142",
            "email": "marker.contact@example.com",
        },
    )

    stored = json.dumps(list(AuditEvent.objects.values()), default=str)
    through_the_api = admin_client.get(FEED_URL).content.decode()

    for marker in MARKERS:
        assert marker not in stored
        assert marker not in through_the_api
    for word in ("password", "token", "secret"):
        assert word not in stored.lower()
import pytest

from profiles.models import Demographics, EmergencyContact, HealthProfile, WellnessPreferences

pytestmark = pytest.mark.django_db

ME_URL = "/api/profiles/me"
DEMOGRAPHICS_URL = "/api/profiles/me/demographics"
WELLNESS_URL = "/api/profiles/me/wellness"
CONTACTS_URL = "/api/profiles/me/emergency-contacts"

VALID_DEMOGRAPHICS = {
    "date_of_birth": "1995-04-12",
    "gender": "FEMALE",
    "blood_group": "O+",
    "height_cm": "172.5",
    "weight_kg": "64.0",
    "country": "Canada",
    "preferred_language": "English",
}
VALID_WELLNESS = {
    "activity_level": "MODERATE",
    "diet_preference": "VEGETARIAN",
    "sleep_goal_hours": "7.5",
    "reminder_channel": "EMAIL",
    "wellness_goals": "Fictional goal: walk daily.",
    "allergy_notes": "Fictional pollen sensitivity",
    "condition_notes": "",
}
VALID_CONTACT = {"name": "Fictional Helper", "relationship": "FRIEND", "phone": "555-0101"}

WRITE_REQUESTS = [
    ("patch", DEMOGRAPHICS_URL, {"country": "Canada"}),
    ("delete", DEMOGRAPHICS_URL, None),
    ("patch", WELLNESS_URL, {"activity_level": "LIGHT"}),
    ("post", CONTACTS_URL, VALID_CONTACT),
]


def call(client, method, url, body=None, **extra):
    send = getattr(client, method)
    if method in ("post", "patch", "put"):
        return send(url, body if body is not None else {}, format="json", **extra)
    return send(url, **extra)


@pytest.fixture
def member(api_client, user, login):
    login(api_client)
    return api_client


def completion_of(client):
    return client.get(ME_URL).json()["completion"]


def add_contact(client, **overrides):
    return call(client, "post", CONTACTS_URL, {**VALID_CONTACT, **overrides})


# ---------- demographics ----------


def test_demographics_start_empty(member):
    data = member.get(DEMOGRAPHICS_URL).json()
    assert data["date_of_birth"] is None
    assert data["gender"] == ""
    assert data["height_cm"] is None


def test_demographics_can_be_updated_and_completion_follows(member, user):
    response = call(member, "patch", DEMOGRAPHICS_URL, VALID_DEMOGRAPHICS)
    assert response.status_code == 200
    saved = Demographics.objects.get(profile__user=user)
    assert saved.country == "Canada"
    assert str(saved.height_cm) == "172.5"
    completion = completion_of(member)
    assert completion["percent"] == 50
    assert completion["status"] == "IN_PROGRESS"


@pytest.mark.parametrize(
    "values",
    [
        {"height_cm": "-5"},
        {"height_cm": "0"},
        {"height_cm": "500"},
        {"weight_kg": "-1"},
        {"weight_kg": "9999"},
        {"date_of_birth": "2999-01-01"},
        {"date_of_birth": "1800-01-01"},
        {"date_of_birth": "not-a-date"},
        {"gender": "ROBOT"},
        {"blood_group": "Z+"},
        {"country": "x" * 61},
        {"preferred_language": "Eng\u0000lish"},
    ],
)
def test_demographics_reject_invalid_input(member, values):
    assert call(member, "patch", DEMOGRAPHICS_URL, values).status_code == 400


def test_demographics_ignore_fields_a_member_may_not_set(member, user):
    body = {"country": "Canada", "id": 999, "completion_percent": 100, "updated_at": "2000-01-01T00:00:00Z"}
    assert call(member, "patch", DEMOGRAPHICS_URL, body).status_code == 200
    assert HealthProfile.objects.get(user=user).completion_percent == 0


def test_a_member_cannot_write_into_another_members_sections(member, user, other_user):
    other_profile = HealthProfile.objects.get(user=other_user)
    body = {"country": "Canada", "profile": other_profile.id, "profile_id": other_profile.id}
    assert call(member, "patch", DEMOGRAPHICS_URL, body).status_code == 200
    assert Demographics.objects.get(profile__user=user).country == "Canada"
    assert Demographics.objects.get(profile=other_profile).country == ""


def test_demographics_can_be_reset(member, user):
    call(member, "patch", DEMOGRAPHICS_URL, VALID_DEMOGRAPHICS)
    response = member.delete(DEMOGRAPHICS_URL)
    assert response.status_code == 200
    assert response.json()["country"] == ""
    assert HealthProfile.objects.get(user=user).completion_percent == 0


# ---------- every write: CSRF and deactivation ----------


@pytest.mark.parametrize("method, url, body", WRITE_REQUESTS)
def test_writes_need_a_csrf_token_in_browser_mode(csrf_client, user, login, csrf_header, method, url, body):
    login(csrf_client)
    assert call(csrf_client, method, url, body).status_code == 403
    response = call(csrf_client, method, url, body, **csrf_header(csrf_client))
    assert response.status_code in (200, 201)


@pytest.mark.parametrize("method, url, body", WRITE_REQUESTS)
def test_deactivated_profile_blocks_every_write(member, user, method, url, body):
    HealthProfile.objects.filter(user=user).update(status="INACTIVE")
    assert member.get(ME_URL).status_code == 200
    response = call(member, method, url, body)
    assert response.status_code == 403
    assert "deactivated" in response.json()["detail"]


# ---------- wellness ----------


def test_wellness_starts_empty(member):
    data = member.get(WELLNESS_URL).json()
    assert data["activity_level"] == ""
    assert data["sleep_goal_hours"] is None


def test_wellness_can_be_updated_and_completion_follows(member, user):
    response = call(member, "patch", WELLNESS_URL, VALID_WELLNESS)
    assert response.status_code == 200
    assert WellnessPreferences.objects.get(profile__user=user).allergy_notes == "Fictional pollen sensitivity"
    assert completion_of(member)["percent"] == 30


@pytest.mark.parametrize(
    "values",
    [
        {"sleep_goal_hours": "2.9"},
        {"sleep_goal_hours": "14.1"},
        {"activity_level": "EXTREME"},
        {"diet_preference": "CARNIVORE"},
        {"reminder_channel": "PIGEON"},
        {"wellness_goals": "x" * 501},
        {"allergy_notes": "Bad\x07note"},
    ],
)
def test_wellness_rejects_invalid_input(member, values):
    assert call(member, "patch", WELLNESS_URL, values).status_code == 400


def test_wellness_can_be_reset(member, user):
    call(member, "patch", WELLNESS_URL, VALID_WELLNESS)
    response = member.delete(WELLNESS_URL)
    assert response.status_code == 200
    assert response.json()["activity_level"] == ""
    assert HealthProfile.objects.get(user=user).completion_percent == 0


# ---------- emergency contacts ----------


def test_first_contact_becomes_primary_and_counts_towards_completion(member):
    response = add_contact(member)
    assert response.status_code == 201
    assert response.json()["is_primary"] is True
    completion = completion_of(member)
    assert completion["percent"] == 20
    missing = [item["key"] for item in completion["missing"]]
    assert "emergency_contact" not in missing
    assert "primary_contact" not in missing


def test_contacts_are_listed_primary_first(member):
    add_contact(member, name="First", phone="555-0101")
    add_contact(member, name="Second", phone="555-0102")
    assert [contact["name"] for contact in member.get(CONTACTS_URL).json()] == ["First", "Second"]


def test_a_new_primary_contact_replaces_the_old_one(member):
    add_contact(member, name="First", phone="555-0101")
    second = add_contact(member, name="Second", phone="555-0102", is_primary=True).json()
    contacts = member.get(CONTACTS_URL).json()
    assert [contact["is_primary"] for contact in contacts] == [True, False]
    assert contacts[0]["id"] == second["id"]


def test_at_most_three_contacts_can_be_saved(member):
    for number in range(3):
        assert add_contact(member, name=f"Contact {number}", phone=f"555-010{number}").status_code == 201
    response = add_contact(member, name="Fourth", phone="555-0199")
    assert response.status_code == 400
    assert "non_field_errors" in response.json()
    assert EmergencyContact.objects.count() == 3


def test_duplicate_phone_is_rejected_even_when_formatted_differently(member):
    add_contact(member, phone="555-0101")
    response = add_contact(member, name="Other", phone="555 0101")
    assert response.status_code == 400
    assert "phone" in response.json()


@pytest.mark.parametrize(
    "values, field",
    [
        ({"name": ""}, "name"),
        ({"name": "x" * 101}, "name"),
        ({"name": "Bad\x07Name"}, "name"),
        ({"phone": ""}, "phone"),
        ({"phone": "abc"}, "phone"),
        ({"phone": "12345"}, "phone"),
        ({"phone": "1" * 16}, "phone"),
        ({"email": "not-an-email"}, "email"),
        ({"relationship": "NEMESIS"}, "relationship"),
    ],
)
def test_contact_validation(member, values, field):
    response = add_contact(member, **values)
    assert response.status_code == 400
    assert field in response.json()


@pytest.mark.parametrize("missing", ["name", "phone"])
def test_contact_requires_a_name_and_a_phone(member, missing):
    body = dict(VALID_CONTACT)
    body.pop(missing)
    response = call(member, "post", CONTACTS_URL, body)
    assert response.status_code == 400
    assert missing in response.json()


def test_a_contact_can_be_read_and_edited(member):
    created = add_contact(member).json()
    url = f"{CONTACTS_URL}/{created['id']}"
    assert member.get(url).json()["name"] == "Fictional Helper"

    response = call(member, "patch", url, {"name": "Renamed Helper", "relationship": "SIBLING", "phone": "555-0177"})
    assert response.status_code == 200
    saved = EmergencyContact.objects.get(pk=created["id"])
    assert (saved.name, saved.relationship, saved.phone) == ("Renamed Helper", "SIBLING", "555-0177")


def test_saving_a_contact_with_its_own_phone_is_allowed(member):
    created = add_contact(member).json()
    response = call(member, "patch", f"{CONTACTS_URL}/{created['id']}", {"name": "Same Phone", "phone": "555-0101"})
    assert response.status_code == 200


def test_editing_a_contact_cannot_reuse_another_contacts_phone(member):
    add_contact(member, phone="555-0101")
    second = add_contact(member, name="Second", phone="555-0102").json()
    response = call(member, "patch", f"{CONTACTS_URL}/{second['id']}", {"phone": "555 0101"})
    assert response.status_code == 400
    assert "phone" in response.json()


def test_the_primary_flag_cannot_be_switched_off_directly(member):
    created = add_contact(member).json()
    response = call(member, "patch", f"{CONTACTS_URL}/{created['id']}", {"is_primary": False})
    assert response.status_code == 400
    assert "is_primary" in response.json()


def test_making_another_contact_primary_demotes_the_current_one(member):
    add_contact(member, name="First", phone="555-0101")
    second = add_contact(member, name="Second", phone="555-0102").json()
    response = call(member, "patch", f"{CONTACTS_URL}/{second['id']}", {"is_primary": True})
    assert response.status_code == 200
    primaries = [contact["name"] for contact in member.get(CONTACTS_URL).json() if contact["is_primary"]]
    assert primaries == ["Second"]


def test_deleting_the_primary_promotes_the_next_contact(member):
    first = add_contact(member, name="First", phone="555-0101").json()
    add_contact(member, name="Second", phone="555-0102")
    assert member.delete(f"{CONTACTS_URL}/{first['id']}").status_code == 204
    contacts = member.get(CONTACTS_URL).json()
    assert [(contact["name"], contact["is_primary"]) for contact in contacts] == [("Second", True)]


def test_deleting_the_last_contact_takes_back_the_completion_items(member):
    created = add_contact(member).json()
    assert completion_of(member)["percent"] == 20
    assert member.delete(f"{CONTACTS_URL}/{created['id']}").status_code == 204
    assert completion_of(member)["percent"] == 0


def test_another_members_contact_is_invisible_and_untouchable(api_client, user, other_user, login):
    victim = EmergencyContact.objects.create(
        profile=HealthProfile.objects.get(user=other_user),
        name="Victim Contact",
        phone="555-0142",
        is_primary=True,
    )
    login(api_client)
    url = f"{CONTACTS_URL}/{victim.id}"

    assert api_client.get(url).status_code == 404
    assert call(api_client, "patch", url, {"name": "Hacked"}).status_code == 404
    assert api_client.delete(url).status_code == 404

    victim.refresh_from_db()
    assert victim.name == "Victim Contact"
    assert api_client.get(CONTACTS_URL).json() == []


# ---------- everything together ----------


def test_filling_in_everything_reaches_one_hundred_percent(member):
    call(member, "patch", DEMOGRAPHICS_URL, VALID_DEMOGRAPHICS)
    call(member, "patch", WELLNESS_URL, VALID_WELLNESS)
    add_contact(member)
    assert completion_of(member) == {"percent": 100, "status": "COMPLETE", "missing": []}
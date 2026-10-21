from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.db import IntegrityError, transaction

from accounts.models import User
from profiles.models import Demographics, EmergencyContact, HealthProfile, WellnessPreferences
from profiles.services import completion_for, create_profile_with_sections, recalculate_completion

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng!Pass#2026"

FIVE_DEMOGRAPHIC_ITEMS = {
    "date_of_birth": date(1990, 5, 17),
    "gender": "FEMALE",
    "blood_group": "O+",
    "height_cm": Decimal("170.0"),
    "weight_kg": Decimal("65.0"),
}


def make_other_profile():
    user = User.objects.create_user(email="omar@example.com", password=PASSWORD, full_name="Omar Demo")
    return create_profile_with_sections(user)


def make_contact(profile, **overrides):
    values = {"name": "Fictional Contact", "relationship": "FRIEND", "phone": "555-0101", "is_primary": False}
    values.update(overrides)
    return EmergencyContact.objects.create(profile=profile, **values)


@pytest.fixture
def profile(db):
    user = User.objects.create_user(email="sara@example.com", password=PASSWORD, full_name="Sara Demo")
    return create_profile_with_sections(user)


def test_profile_is_created_with_empty_sections(profile):
    assert Demographics.objects.filter(profile=profile).exists()
    assert WellnessPreferences.objects.filter(profile=profile).exists()
    assert not profile.emergency_contacts.exists()
    assert profile.completion_percent == 0
    assert profile.completion_status == "NOT_STARTED"


def test_signup_creates_the_sections(api_client):
    payload = {"full_name": "New Member", "email": "new.member@example.com", "password": PASSWORD}
    assert api_client.post("/api/auth/signup", payload, format="json").status_code == 201
    created = HealthProfile.objects.get(user__email="new.member@example.com")
    assert Demographics.objects.filter(profile=created).exists()
    assert WellnessPreferences.objects.filter(profile=created).exists()


def test_demographics_is_one_per_profile(profile):
    with pytest.raises(IntegrityError), transaction.atomic():
        Demographics.objects.create(profile=profile)


def test_wellness_is_one_per_profile(profile):
    with pytest.raises(IntegrityError), transaction.atomic():
        WellnessPreferences.objects.create(profile=profile)


@pytest.mark.parametrize(
    "values",
    [
        {"height_cm": Decimal("-1")},
        {"weight_kg": Decimal("0")},
        {"gender": "ROBOT"},
        {"blood_group": "Z+"},
    ],
)
def test_database_rejects_invalid_demographics(profile, values):
    with pytest.raises(IntegrityError), transaction.atomic():
        Demographics.objects.filter(profile=profile).update(**values)


@pytest.mark.parametrize(
    "values",
    [
        {"sleep_goal_hours": Decimal("2.9")},
        {"sleep_goal_hours": Decimal("14.1")},
        {"activity_level": "EXTREME"},
        {"diet_preference": "CARNIVORE"},
        {"reminder_channel": "PIGEON"},
    ],
)
def test_database_rejects_invalid_wellness_values(profile, values):
    with pytest.raises(IntegrityError), transaction.atomic():
        WellnessPreferences.objects.filter(profile=profile).update(**values)


def test_only_one_primary_contact_per_profile(profile):
    make_contact(profile, is_primary=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_contact(profile, phone="555-0102", is_primary=True)


def test_other_profiles_can_have_their_own_primary_contact(profile):
    make_contact(profile, is_primary=True)
    make_contact(make_other_profile(), is_primary=True)
    assert EmergencyContact.objects.filter(is_primary=True).count() == 2


def test_same_phone_cannot_be_added_twice_to_one_profile(profile):
    make_contact(profile, phone="555-0101")
    with pytest.raises(IntegrityError), transaction.atomic():
        make_contact(profile, name="Another Contact", phone="555-0101")


def test_blank_phones_are_allowed_more_than_once(profile):
    make_contact(profile, name="First", phone="")
    make_contact(profile, name="Second", phone="")
    assert profile.emergency_contacts.count() == 2


def test_same_phone_is_allowed_on_different_profiles(profile):
    make_contact(profile, phone="555-0101")
    make_contact(make_other_profile(), phone="555-0101")
    assert EmergencyContact.objects.filter(phone="555-0101").count() == 2


def test_contact_needs_a_name(profile):
    with pytest.raises(IntegrityError), transaction.atomic():
        make_contact(profile, name="")


def test_contact_relationship_must_be_valid(profile):
    with pytest.raises(IntegrityError), transaction.atomic():
        make_contact(profile, relationship="NEMESIS")


@pytest.mark.parametrize(
    "status, percent",
    [
        ("COMPLETE", 50),
        ("NOT_STARTED", 10),
        ("IN_PROGRESS", 0),
        ("IN_PROGRESS", 100),
        ("DONE", 100),
    ],
)
def test_completion_status_and_percent_must_agree(profile, status, percent):
    with pytest.raises(IntegrityError), transaction.atomic():
        HealthProfile.objects.filter(pk=profile.pk).update(
            completion_status=status,
            completion_percent=percent,
        )


def test_consistent_completion_values_are_accepted(profile):
    HealthProfile.objects.filter(pk=profile.pk).update(completion_status="COMPLETE", completion_percent=100)
    assert HealthProfile.objects.get(pk=profile.pk).completion_status == "COMPLETE"


def test_deleting_a_user_removes_every_section(profile):
    make_contact(profile, is_primary=True)
    profile.user.delete()
    assert not HealthProfile.objects.exists()
    assert not Demographics.objects.exists()
    assert not WellnessPreferences.objects.exists()
    assert not EmergencyContact.objects.exists()


def test_primary_contact_is_listed_first(profile):
    make_contact(profile, name="Second", phone="555-0102")
    make_contact(profile, name="First", phone="555-0101", is_primary=True)
    assert [contact.name for contact in profile.emergency_contacts.all()] == ["First", "Second"]


def test_recalculate_completion_follows_the_sections(profile):
    Demographics.objects.filter(profile=profile).update(**FIVE_DEMOGRAPHIC_ITEMS)
    WellnessPreferences.objects.filter(profile=profile).update(
        activity_level="MODERATE",
        diet_preference="NO_PREFERENCE",
        reminder_channel="EMAIL",
    )
    make_contact(profile, is_primary=True)

    result = recalculate_completion(profile)
    assert result.percent == 100
    stored = HealthProfile.objects.get(pk=profile.pk)
    assert (stored.completion_percent, stored.completion_status) == (100, "COMPLETE")

    EmergencyContact.objects.filter(profile=profile).delete()
    recalculate_completion(profile)
    stored.refresh_from_db()
    assert (stored.completion_percent, stored.completion_status) == (80, "IN_PROGRESS")


def test_recalculate_command_creates_missing_sections_and_fixes_stale_values(profile):
    lonely_user = User.objects.create_user(email="lonely@example.com", password=PASSWORD, full_name="Lonely Demo")
    lonely = HealthProfile.objects.create(user=lonely_user)
    Demographics.objects.filter(profile=profile).update(**FIVE_DEMOGRAPHIC_ITEMS)

    call_command("recalculate_completion")

    assert Demographics.objects.filter(profile=lonely).exists()
    assert WellnessPreferences.objects.filter(profile=lonely).exists()
    assert HealthProfile.objects.get(pk=profile.pk).completion_percent == 50
    assert HealthProfile.objects.get(pk=lonely.pk).completion_percent == 0


def test_recalculate_dry_run_changes_nothing(profile):
    Demographics.objects.filter(profile=profile).update(**FIVE_DEMOGRAPHIC_ITEMS)
    call_command("recalculate_completion", dry_run=True)
    assert HealthProfile.objects.get(pk=profile.pk).completion_percent == 0


def test_seed_data_creates_sections_with_consistent_completion():
    call_command("seed_data", count=40)

    assert HealthProfile.objects.count() == 40
    assert Demographics.objects.count() == 40
    assert WellnessPreferences.objects.count() == 40
    assert len(set(HealthProfile.objects.values_list("completion_status", flat=True))) >= 2

    for stored in HealthProfile.objects.prefetch_related("demographics", "wellness", "emergency_contacts"):
        result = completion_for(stored)
        assert (stored.completion_percent, stored.completion_status) == (result.percent, result.status)
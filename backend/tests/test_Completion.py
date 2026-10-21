from datetime import date
from decimal import Decimal

import pytest

from profiles.completion import calculate_completion


def full_inputs():
    demographics = {
        "date_of_birth": date(1990, 5, 17),
        "gender": "FEMALE",
        "blood_group": "O+",
        "height_cm": Decimal("170.0"),
        "weight_kg": Decimal("65.0"),
    }
    contacts = [{"phone": "555-0101", "is_primary": True}]
    wellness = {
        "activity_level": "MODERATE",
        "diet_preference": "NO_PREFERENCE",
        "reminder_channel": "EMAIL",
    }
    return demographics, contacts, wellness


def test_nothing_filled_is_not_started():
    result = calculate_completion(None, [], None)
    assert result.percent == 0
    assert result.status == "NOT_STARTED"
    assert len(result.missing) == 10


def test_everything_filled_is_complete():
    result = calculate_completion(*full_inputs())
    assert result.percent == 100
    assert result.status == "COMPLETE"
    assert result.missing == ()


@pytest.mark.parametrize("key", ["date_of_birth", "gender", "blood_group", "height_cm", "weight_kg"])
def test_removing_one_demographic_item_costs_ten_percent(key):
    demographics, contacts, wellness = full_inputs()
    demographics[key] = None
    result = calculate_completion(demographics, contacts, wellness)
    assert result.percent == 90
    assert result.status == "IN_PROGRESS"
    assert result.missing == (key,)


@pytest.mark.parametrize("key", ["activity_level", "diet_preference", "reminder_channel"])
def test_removing_one_wellness_item_costs_ten_percent(key):
    demographics, contacts, wellness = full_inputs()
    wellness[key] = ""
    result = calculate_completion(demographics, contacts, wellness)
    assert result.percent == 90
    assert result.missing == (key,)


def test_without_contacts_two_items_are_missing():
    demographics, _, wellness = full_inputs()
    result = calculate_completion(demographics, [], wellness)
    assert result.percent == 80
    assert result.missing == ("emergency_contact", "primary_contact")


def test_contact_without_phone_counts_only_as_primary():
    demographics, _, wellness = full_inputs()
    result = calculate_completion(demographics, [{"phone": "", "is_primary": True}], wellness)
    assert result.percent == 90
    assert result.missing == ("emergency_contact",)


def test_blank_text_does_not_count_as_filled():
    demographics, contacts, wellness = full_inputs()
    demographics["gender"] = "   "
    wellness["activity_level"] = ""
    result = calculate_completion(demographics, contacts, wellness)
    assert result.percent == 80
    assert result.missing == ("gender", "activity_level")


def test_partial_example_reports_remaining_items_in_order():
    demographics, contacts, _ = full_inputs()
    demographics["gender"] = ""
    result = calculate_completion(demographics, contacts, None)
    assert result.percent == 60
    assert result.status == "IN_PROGRESS"
    assert result.missing == ("gender", "activity_level", "diet_preference", "reminder_channel")
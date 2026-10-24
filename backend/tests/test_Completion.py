from datetime import date

import pytest

from profiles.completion import ITEM_KEYS, OPTIONAL_FIELDS, calculate_completion


def required_only_inputs():
    demographics = {"date_of_birth": date(1990, 5, 17), "gender": "FEMALE"}
    contacts = [{"phone": "555-0101", "is_primary": True}]
    wellness = {"contact_preference": "EMAIL", "wellness_goals": "Fictional goal: walk daily."}
    return demographics, contacts, wellness


def test_the_required_items_are_exactly_these_six():
    assert ITEM_KEYS == (
        "date_of_birth",
        "gender",
        "emergency_contact",
        "primary_contact",
        "contact_preference",
        "wellness_goals",
    )


def test_nothing_filled_is_not_started():
    result = calculate_completion(None, [], None)
    assert (result.percent, result.status) == (0, "NOT_STARTED")
    assert len(result.missing) == 6


def test_the_required_items_alone_reach_one_hundred_percent():
    result = calculate_completion(*required_only_inputs())
    assert (result.percent, result.status, result.missing) == (100, "COMPLETE", ())


def test_optional_fields_alone_count_for_nothing():
    optional_values = {name: "x" for name in OPTIONAL_FIELDS}
    result = calculate_completion(optional_values, [], optional_values)
    assert (result.percent, result.status) == (0, "NOT_STARTED")


def test_optional_fields_do_not_change_a_complete_profile():
    demographics, contacts, wellness = required_only_inputs()
    demographics.update(blood_group="O+", height_cm=170, weight_kg=65, country="Canada", preferred_language="English")
    wellness.update(
        activity_level="LIGHT",
        diet_preference="VEGAN",
        sleep_goal_hours=7,
        reminder_channel="EMAIL",
        allergy_notes="Fictional note",
        condition_notes="Fictional note",
    )
    assert calculate_completion(demographics, contacts, wellness) == calculate_completion(*required_only_inputs())


@pytest.mark.parametrize("key", ["date_of_birth", "gender"])
def test_removing_one_demographic_item_costs_one_item(key):
    demographics, contacts, wellness = required_only_inputs()
    demographics[key] = None
    result = calculate_completion(demographics, contacts, wellness)
    assert (result.percent, result.status, result.missing) == (83, "IN_PROGRESS", (key,))


@pytest.mark.parametrize("key", ["contact_preference", "wellness_goals"])
def test_removing_one_wellness_item_costs_one_item(key):
    demographics, contacts, wellness = required_only_inputs()
    wellness[key] = ""
    result = calculate_completion(demographics, contacts, wellness)
    assert (result.percent, result.missing) == (83, (key,))


def test_without_contacts_two_items_are_missing():
    demographics, _, wellness = required_only_inputs()
    result = calculate_completion(demographics, [], wellness)
    assert result.percent == 67
    assert result.missing == ("emergency_contact", "primary_contact")


def test_a_contact_without_a_phone_counts_only_as_primary():
    demographics, _, wellness = required_only_inputs()
    result = calculate_completion(demographics, [{"phone": "", "is_primary": True}], wellness)
    assert result.percent == 83
    assert result.missing == ("emergency_contact",)


def test_blank_text_does_not_count_as_filled():
    demographics, contacts, wellness = required_only_inputs()
    demographics["gender"] = "   "
    wellness["wellness_goals"] = ""
    result = calculate_completion(demographics, contacts, wellness)
    assert result.percent == 67
    assert result.missing == ("gender", "wellness_goals")


def test_a_partial_profile_reports_the_remaining_items_in_order():
    demographics, contacts, _ = required_only_inputs()
    demographics["gender"] = ""
    result = calculate_completion(demographics, contacts, None)
    assert (result.percent, result.status) == (50, "IN_PROGRESS")
    assert result.missing == ("gender", "contact_preference", "wellness_goals")
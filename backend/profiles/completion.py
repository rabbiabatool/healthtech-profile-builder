from dataclasses import dataclass

from .models import CompletionStatus

# REQUIRED: these items, and only these, are counted. Each is worth the same share.
DEMOGRAPHIC_KEYS = ("date_of_birth", "gender")
WELLNESS_KEYS = ("contact_preference", "wellness_goals")

ITEM_KEYS = DEMOGRAPHIC_KEYS + ("emergency_contact", "primary_contact") + WELLNESS_KEYS

ITEM_LABELS = {
    "date_of_birth": "Date of birth",
    "gender": "Gender",
    "emergency_contact": "An emergency contact with a phone number",
    "primary_contact": "A primary emergency contact",
    "contact_preference": "Contact preference",
    "wellness_goals": "Wellness goals",
}

# OPTIONAL: never counted and never reported as missing.
OPTIONAL_BIOMETRIC_AND_OTHER_FIELDS = ("blood_group", "height_cm", "weight_kg", "country", "preferred_language")
OPTIONAL_LIFESTYLE_FIELDS = (
    "activity_level",
    "diet_preference",
    "sleep_goal_hours",
    "reminder_channel",
    "allergy_notes",
    "condition_notes",
)
OPTIONAL_FIELDS = OPTIONAL_BIOMETRIC_AND_OTHER_FIELDS + OPTIONAL_LIFESTYLE_FIELDS

@dataclass(frozen=True)
class Completion:
    percent: int
    status: str
    missing: tuple


def _filled(value):
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def calculate_completion(demographics, contacts, wellness):
    demographics = demographics or {}
    wellness = wellness or {}
    contacts = contacts or []

    done = {}
    for key in DEMOGRAPHIC_KEYS:
        done[key] = _filled(demographics.get(key))
    done["emergency_contact"] = any(_filled(contact.get("phone")) for contact in contacts)
    done["primary_contact"] = any(bool(contact.get("is_primary")) for contact in contacts)
    for key in WELLNESS_KEYS:
        done[key] = _filled(wellness.get(key))

    missing = tuple(key for key in ITEM_KEYS if not done[key])
    total = len(ITEM_KEYS)
    completed = total - len(missing)

    if completed == 0:
        return Completion(0, CompletionStatus.NOT_STARTED, missing)
    if completed == total:
        return Completion(100, CompletionStatus.COMPLETE, missing)

    percent = min(99, max(1, round(100 * completed / total)))
    return Completion(percent, CompletionStatus.IN_PROGRESS, missing)
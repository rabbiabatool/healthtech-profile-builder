from django.db import transaction
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from audit.models import AuditAction
from audit.services import record_event

from .completion import calculate_completion
from .models import Demographics, EmergencyContact, HealthProfile, WellnessPreferences

MAX_EMERGENCY_CONTACTS = 3

DEMOGRAPHICS_BLANK = {
    "date_of_birth": None,
    "gender": "",
    "blood_group": "",
    "height_cm": None,
    "weight_kg": None,
    "country": "",
    "preferred_language": "",
}

WELLNESS_BLANK = {
    "activity_level": "",
    "diet_preference": "",
    "sleep_goal_hours": None,
    "reminder_channel": "",
    "wellness_goals": "",
    "allergy_notes": "",
    "condition_notes": "",
    "contact_preference": "",
}


@transaction.atomic
def create_profile_with_sections(user):
    profile = HealthProfile.objects.create(user=user)
    Demographics.objects.create(profile=profile)
    WellnessPreferences.objects.create(profile=profile)
    return profile


def _section_values(section):
    return None if section is None else model_to_dict(section)


def completion_for(profile):
    contacts = [
        {"phone": contact.phone, "is_primary": contact.is_primary}
        for contact in profile.emergency_contacts.all()
    ]
    return calculate_completion(
        _section_values(getattr(profile, "demographics", None)),
        contacts,
        _section_values(getattr(profile, "wellness", None)),
    )


def recalculate_completion(profile):
    fresh = HealthProfile.objects.get(pk=profile.pk)
    result = completion_for(fresh)

    if (fresh.completion_percent, fresh.completion_status) != (result.percent, result.status):
        HealthProfile.objects.filter(pk=fresh.pk).update(
            completion_percent=result.percent,
            completion_status=result.status,
        )

    profile.completion_percent = result.percent
    profile.completion_status = result.status
    return result


def _lock_profile(profile):
    return HealthProfile.objects.select_for_update().get(pk=profile.pk)


def _changed_names(instance, values):
    return [field for field, value in values.items() if getattr(instance, field) != value]


def _apply_changes(instance, values):
    changed = _changed_names(instance, values)
    for field, value in values.items():
        setattr(instance, field, value)
    if changed:
        instance.save()
    return changed


def _digits(phone):
    return "".join(character for character in phone if character.isdigit())


def _reject_duplicate_phone(contacts, phone):
    if not phone:
        return
    if any(_digits(contact.phone) == _digits(phone) for contact in contacts):
        raise ValidationError({"phone": ["This phone number is already saved for another contact."]})


def _save_section(model, section_name, profile, values, *, actor, action):
    _lock_profile(profile)
    section = model.objects.get(profile=profile)
    changed = _apply_changes(section, values)
    recalculate_completion(profile)
    if changed:
        record_event(
            actor,
            action,
            profile_id=profile.pk,
            changed_fields=changed,
            metadata={"section": section_name},
        )
    return section


@transaction.atomic
def update_demographics(profile, values, *, actor):
    return _save_section(
        Demographics, "demographics", profile, values, actor=actor, action=AuditAction.DEMOGRAPHICS_UPDATED
    )


@transaction.atomic
def reset_demographics(profile, *, actor):
    return _save_section(
        Demographics,
        "demographics",
        profile,
        dict(DEMOGRAPHICS_BLANK),
        actor=actor,
        action=AuditAction.DEMOGRAPHICS_RESET,
    )


@transaction.atomic
def update_wellness(profile, values, *, actor):
    return _save_section(
        WellnessPreferences, "wellness", profile, values, actor=actor, action=AuditAction.WELLNESS_UPDATED
    )


@transaction.atomic
def reset_wellness(profile, *, actor):
    return _save_section(
        WellnessPreferences,
        "wellness",
        profile,
        dict(WELLNESS_BLANK),
        actor=actor,
        action=AuditAction.WELLNESS_RESET,
    )


@transaction.atomic
def create_contact(profile, values, *, actor):
    locked = _lock_profile(profile)
    existing = list(locked.emergency_contacts.all())

    if len(existing) >= MAX_EMERGENCY_CONTACTS:
        raise ValidationError(
            {"non_field_errors": [f"You can save at most {MAX_EMERGENCY_CONTACTS} emergency contacts."]}
        )
    _reject_duplicate_phone(existing, values.get("phone"))

    make_primary = bool(values.get("is_primary", False)) or not existing
    if make_primary:
        locked.emergency_contacts.filter(is_primary=True).update(is_primary=False)

    contact = EmergencyContact.objects.create(profile=locked, **{**values, "is_primary": make_primary})
    recalculate_completion(profile)

    fields = set(values) - {"is_primary"}
    if make_primary:
        fields.add("is_primary")
    record_event(
        actor,
        AuditAction.EMERGENCY_CONTACT_CREATED,
        profile_id=profile.pk,
        changed_fields=fields,
        metadata={"section": "emergency_contacts", "contact_id": contact.pk},
    )
    return contact


@transaction.atomic
def update_contact(profile, contact_id, values, *, actor):
    locked = _lock_profile(profile)
    contact = get_object_or_404(EmergencyContact, pk=contact_id, profile=locked)
    values = dict(values)

    if "phone" in values:
        _reject_duplicate_phone(locked.emergency_contacts.exclude(pk=contact.pk), values["phone"])

    wants_primary = values.pop("is_primary", None)
    if wants_primary is False and contact.is_primary:
        raise ValidationError({"is_primary": ["Make another contact primary instead."]})

    changed = _changed_names(contact, values)
    if wants_primary and not contact.is_primary:
        locked.emergency_contacts.filter(is_primary=True).update(is_primary=False)
        contact.is_primary = True
        changed.append("is_primary")

    for field, value in values.items():
        setattr(contact, field, value)
    contact.save()
    recalculate_completion(profile)

    if changed:
        record_event(
            actor,
            AuditAction.EMERGENCY_CONTACT_UPDATED,
            profile_id=profile.pk,
            changed_fields=changed,
            metadata={"section": "emergency_contacts", "contact_id": contact.pk},
        )
    return contact


@transaction.atomic
def delete_contact(profile, contact_id, *, actor):
    locked = _lock_profile(profile)
    contact = get_object_or_404(EmergencyContact, pk=contact_id, profile=locked)
    was_primary = contact.is_primary
    contact.delete()

    if was_primary:
        successor = locked.emergency_contacts.order_by("id").first()
        if successor is not None:
            successor.is_primary = True
            successor.save(update_fields=["is_primary", "updated_at"])

    recalculate_completion(profile)
    record_event(
        actor,
        AuditAction.EMERGENCY_CONTACT_DELETED,
        profile_id=profile.pk,
        metadata={"section": "emergency_contacts", "contact_id": contact_id},
    )

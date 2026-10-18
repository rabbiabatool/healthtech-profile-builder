from django.db import transaction
from django.forms.models import model_to_dict

from .completion import calculate_completion
from .models import Demographics, HealthProfile, WellnessPreferences


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
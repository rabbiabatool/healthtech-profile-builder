from django.db import migrations

BATCH_SIZE = 1000


def copy_profile_data(apps, schema_editor):
    HealthProfile = apps.get_model("profiles", "HealthProfile")
    Demographics = apps.get_model("profiles", "Demographics")
    WellnessPreferences = apps.get_model("profiles", "WellnessPreferences")
    EmergencyContact = apps.get_model("profiles", "EmergencyContact")

    has_demographics = set(Demographics.objects.values_list("profile_id", flat=True))
    has_wellness = set(WellnessPreferences.objects.values_list("profile_id", flat=True))
    has_contact = set(EmergencyContact.objects.values_list("profile_id", flat=True))

    new_demographics = []
    new_wellness = []
    new_contacts = []

    for profile in HealthProfile.objects.all().iterator(chunk_size=BATCH_SIZE):
        if profile.pk not in has_demographics:
            new_demographics.append(
                Demographics(
                    profile_id=profile.pk,
                    date_of_birth=profile.date_of_birth,
                    blood_group=profile.blood_group,
                    height_cm=profile.height_cm,
                    weight_kg=profile.weight_kg,
                )
            )
        if profile.pk not in has_wellness:
            new_wellness.append(
                WellnessPreferences(
                    profile_id=profile.pk,
                    allergy_notes=profile.allergies,
                    condition_notes=profile.conditions,
                )
            )
        legacy_contact = (profile.emergency_contact or "").strip()
        if legacy_contact and profile.pk not in has_contact:
            new_contacts.append(
                EmergencyContact(
                    profile_id=profile.pk,
                    name=legacy_contact[:100],
                    relationship="OTHER",
                    phone="",
                    is_primary=True,
                )
            )

    Demographics.objects.bulk_create(new_demographics, batch_size=BATCH_SIZE)
    WellnessPreferences.objects.bulk_create(new_wellness, batch_size=BATCH_SIZE)
    EmergencyContact.objects.bulk_create(new_contacts, batch_size=BATCH_SIZE)


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0003_relational_sections"),
    ]

    operations = [
        migrations.RunPython(copy_profile_data, migrations.RunPython.noop),
    ]
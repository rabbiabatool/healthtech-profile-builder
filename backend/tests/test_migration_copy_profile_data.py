import importlib
from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

BEFORE = [("profiles", "0002_refine_status_created_index")]
AFTER = [("profiles", "0004_copy_profile_data")]


@pytest.mark.django_db(transaction=True)
def test_data_migration_moves_legacy_values_into_the_new_tables():
    executor = MigrationExecutor(connection)
    executor.migrate(BEFORE)
    old_apps = executor.loader.project_state(BEFORE).apps

    try:
        User = old_apps.get_model("accounts", "User")
        OldProfile = old_apps.get_model("profiles", "HealthProfile")

        filled_user = User.objects.create(email="filled@example.com", full_name="Filled Legacy", password="x")
        empty_user = User.objects.create(email="empty@example.com", full_name="Empty Legacy", password="x")
        filled = OldProfile.objects.create(
            user=filled_user,
            date_of_birth=date(1990, 5, 17),
            blood_group="O+",
            height_cm=Decimal("170.5"),
            weight_kg=Decimal("64.0"),
            allergies="Fictional pollen sensitivity",
            conditions="Fictional sample condition",
            emergency_contact="Fictional Contact 555-0100",
        )
        empty = OldProfile.objects.create(user=empty_user)

        executor = MigrationExecutor(connection)
        executor.migrate(AFTER)
        new_apps = executor.loader.project_state(AFTER).apps
        NewDemographics = new_apps.get_model("profiles", "Demographics")
        NewWellness = new_apps.get_model("profiles", "WellnessPreferences")
        NewContact = new_apps.get_model("profiles", "EmergencyContact")

        demographics = NewDemographics.objects.get(profile_id=filled.pk)
        assert demographics.date_of_birth == date(1990, 5, 17)
        assert demographics.blood_group == "O+"
        assert demographics.height_cm == Decimal("170.5")
        assert demographics.weight_kg == Decimal("64.0")

        wellness = NewWellness.objects.get(profile_id=filled.pk)
        assert wellness.allergy_notes == "Fictional pollen sensitivity"
        assert wellness.condition_notes == "Fictional sample condition"

        contact = NewContact.objects.get(profile_id=filled.pk)
        assert contact.name == "Fictional Contact 555-0100"
        assert contact.is_primary
        assert contact.phone == ""

        assert NewDemographics.objects.filter(profile_id=empty.pk).exists()
        assert NewWellness.objects.filter(profile_id=empty.pk).exists()
        assert not NewContact.objects.filter(profile_id=empty.pk).exists()

        migration = importlib.import_module("profiles.migrations.0004_copy_profile_data")
        migration.copy_profile_data(new_apps, None)
        assert NewDemographics.objects.count() == 2
        assert NewWellness.objects.count() == 2
        assert NewContact.objects.count() == 1
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
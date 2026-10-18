import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Role, User
from profiles.completion import calculate_completion
from profiles.models import (
    ActivityLevel,
    BloodGroup,
    Demographics,
    DietPreference,
    EmergencyContact,
    Gender,
    HealthProfile,
    ProfileStatus,
    Relationship,
    ReminderChannel,
    WellnessPreferences,
)

FIRST_NAMES = ["Sara", "Ali", "Hina", "Omar", "Zara", "Bilal", "Maya", "Daniyal", "Noor", "Ayaan"]
LAST_NAMES = ["Demo", "Sample", "Testcase", "Placeholder", "Fictional", "Example"]
ALLERGIES = ["", "", "Fictional pollen sensitivity", "Fictional dust sensitivity", "Fictional nut sensitivity"]
CONDITIONS = ["", "", "", "Fictional mild seasonal condition", "Fictional sample condition A"]
COUNTRIES = ["Pakistan", "Canada", "Germany", "Brazil", "Japan"]
LANGUAGES = ["English", "Urdu", "German", "Portuguese", "Japanese"]
LEVELS = ["empty", "starter", "partial", "partial", "full", "full"]


def build_recipe(rng):
    level = rng.choice(LEVELS)
    demographics = {
        "date_of_birth": None,
        "gender": "",
        "blood_group": "",
        "height_cm": None,
        "weight_kg": None,
        "country": "",
        "preferred_language": "",
    }
    wellness = {
        "activity_level": "",
        "diet_preference": "",
        "sleep_goal_hours": None,
        "reminder_channel": "",
        "wellness_goals": "",
        "allergy_notes": "",
        "condition_notes": "",
    }
    contacts = []

    if level != "empty":
        demographics["date_of_birth"] = date(1960, 1, 1) + timedelta(days=rng.randint(0, 17000))
        demographics["blood_group"] = rng.choice(BloodGroup.values)

    if level in ("partial", "full"):
        demographics["height_cm"] = Decimal(rng.randint(150, 195))
        demographics["weight_kg"] = Decimal(rng.randint(45, 110))
        contacts.append(
            {
                "name": f"Fictional {rng.choice(FIRST_NAMES)} Contact",
                "relationship": rng.choice(Relationship.values),
                "phone": f"555-01{rng.randint(10, 99)}",
                "email": "",
                "is_primary": True,
            }
        )

    if level == "full":
        demographics["gender"] = rng.choice(Gender.values)
        demographics["country"] = rng.choice(COUNTRIES)
        demographics["preferred_language"] = rng.choice(LANGUAGES)
        wellness["activity_level"] = rng.choice(ActivityLevel.values)
        wellness["diet_preference"] = rng.choice(DietPreference.values)
        wellness["sleep_goal_hours"] = Decimal("7.5")
        wellness["reminder_channel"] = rng.choice(ReminderChannel.values)
        wellness["wellness_goals"] = "Fictional goal: take a short walk every day."
        wellness["allergy_notes"] = rng.choice(ALLERGIES)
        wellness["condition_notes"] = rng.choice(CONDITIONS)

    return demographics, contacts, wellness


class Command(BaseCommand):
    help = "Create synthetic (fictional) users with profile sections for local development."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=30)
        parser.add_argument("--password", default="Demo!Pass12345")

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(42)
        count = options["count"]
        hashed_password = make_password(options["password"])

        emails = [f"demo.user{i}@example.com" for i in range(1, count + 1)]
        existing = set(User.objects.filter(email__in=emails).values_list("email", flat=True))

        new_users = [
            User(
                email=email,
                password=hashed_password,
                full_name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)} {index}",
                role=Role.USER,
            )
            for index, email in enumerate(emails, start=1)
            if email not in existing
        ]
        User.objects.bulk_create(new_users, batch_size=1000)

        users = list(User.objects.filter(email__in=emails, profile__isnull=True).order_by("id"))
        recipes = [build_recipe(rng) for _ in users]

        profile_objects = []
        for user, (demographics, contacts, wellness) in zip(users, recipes):
            result = calculate_completion(demographics, contacts, wellness)
            profile_objects.append(
                HealthProfile(
                    user=user,
                    date_of_birth=demographics["date_of_birth"],
                    blood_group=demographics["blood_group"],
                    height_cm=demographics["height_cm"],
                    weight_kg=demographics["weight_kg"],
                    allergies=wellness["allergy_notes"],
                    conditions=wellness["condition_notes"],
                    emergency_contact=contacts[0]["name"] if contacts else "",
                    status=ProfileStatus.ACTIVE if rng.random() < 0.85 else ProfileStatus.INACTIVE,
                    completion_percent=result.percent,
                    completion_status=result.status,
                )
            )
        profiles = HealthProfile.objects.bulk_create(profile_objects, batch_size=1000)

        Demographics.objects.bulk_create(
            [Demographics(profile=profile, **recipe[0]) for profile, recipe in zip(profiles, recipes)],
            batch_size=1000,
        )
        WellnessPreferences.objects.bulk_create(
            [WellnessPreferences(profile=profile, **recipe[2]) for profile, recipe in zip(profiles, recipes)],
            batch_size=1000,
        )
        EmergencyContact.objects.bulk_create(
            [
                EmergencyContact(profile=profile, **contact)
                for profile, recipe in zip(profiles, recipes)
                for contact in recipe[1]
            ],
            batch_size=1000,
        )

        self.stdout.write(
            self.style.SUCCESS(f"Created {len(new_users)} users and {len(profiles)} profiles with sections.")
        )
import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Role, User
from profiles.models import BloodGroup, HealthProfile, ProfileStatus

FIRST_NAMES = ["Sara", "Ali", "Hina", "Omar", "Zara", "Bilal", "Maya", "Daniyal", "Noor", "Ayaan"]
LAST_NAMES = ["Demo", "Sample", "Testcase", "Placeholder", "Fictional", "Example"]
ALLERGIES = ["", "", "Fictional pollen sensitivity", "Fictional dust sensitivity", "Fictional nut sensitivity"]
CONDITIONS = ["", "", "", "Fictional mild seasonal condition", "Fictional sample condition A"]


class Command(BaseCommand):
    help = "Create synthetic (fictional) users and health profiles for local development."

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

        users_without_profile = User.objects.filter(email__in=emails, profile__isnull=True)
        profiles = [
            HealthProfile(
                user=user,
                date_of_birth=date(1960, 1, 1) + timedelta(days=rng.randint(0, 17000)),
                blood_group=rng.choice(BloodGroup.values),
                height_cm=Decimal(rng.randint(150, 195)),
                weight_kg=Decimal(rng.randint(45, 110)),
                allergies=rng.choice(ALLERGIES),
                conditions=rng.choice(CONDITIONS),
                emergency_contact="Fictional Contact 555-0100",
                status=ProfileStatus.ACTIVE if rng.random() < 0.85 else ProfileStatus.INACTIVE,
            )
            for user in users_without_profile
        ]
        HealthProfile.objects.bulk_create(profiles, batch_size=1000)

        self.stdout.write(
            self.style.SUCCESS(f"Created {len(new_users)} users and {len(profiles)} profiles.")
        )
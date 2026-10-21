import random

from django.core.management.base import BaseCommand, CommandError

from accounts.models import Role, User
from audit.models import ActorRole, AuditAction, AuditEvent
from profiles.models import HealthProfile

BATCH_SIZE = 5000

DEMOGRAPHIC_FIELDS = [
    "date_of_birth",
    "gender",
    "blood_group",
    "height_cm",
    "weight_kg",
    "country",
    "preferred_language",
]
WELLNESS_FIELDS = [
    "activity_level",
    "diet_preference",
    "sleep_goal_hours",
    "reminder_channel",
    "wellness_goals",
    "allergy_notes",
    "condition_notes",
]
CONTACT_FIELDS = ["name", "relationship", "phone", "email"]

MEMBER_EVENTS = [
    (AuditAction.DEMOGRAPHICS_UPDATED, "demographics", DEMOGRAPHIC_FIELDS),
    (AuditAction.DEMOGRAPHICS_RESET, "demographics", DEMOGRAPHIC_FIELDS),
    (AuditAction.WELLNESS_UPDATED, "wellness", WELLNESS_FIELDS),
    (AuditAction.WELLNESS_RESET, "wellness", WELLNESS_FIELDS),
    (AuditAction.EMERGENCY_CONTACT_CREATED, "emergency_contacts", CONTACT_FIELDS),
    (AuditAction.EMERGENCY_CONTACT_UPDATED, "emergency_contacts", CONTACT_FIELDS),
    (AuditAction.EMERGENCY_CONTACT_DELETED, "emergency_contacts", []),
]
ADMIN_ACTIONS = [
    AuditAction.ADMIN_PROFILE_VIEWED,
    AuditAction.ADMIN_PROFILE_DEACTIVATED,
    AuditAction.ADMIN_PROFILE_REACTIVATED,
    AuditAction.ADMIN_SEARCH_PERFORMED,
]


def admin_metadata(rng, action):
    if action == AuditAction.ADMIN_PROFILE_DEACTIVATED:
        return {"from_status": "ACTIVE", "to_status": "INACTIVE"}
    if action == AuditAction.ADMIN_PROFILE_REACTIVATED:
        return {"from_status": "INACTIVE", "to_status": "ACTIVE"}
    if action == AuditAction.ADMIN_SEARCH_PERFORMED:
        return {"filters_used": ["search"], "result_count": rng.randint(0, 50)}
    return {}


class Command(BaseCommand):
    help = "Create synthetic (fictional) audit events for local development and EXPLAIN demos."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=50000)

    def handle(self, *args, **options):
        profile_users = dict(HealthProfile.objects.values_list("id", "user_id"))
        if not profile_users:
            raise CommandError("There are no profiles yet. Run: python manage.py seed_data --count 500")

        rng = random.Random(7)
        profile_ids = list(profile_users)
        admin_id = User.objects.filter(role=Role.ADMIN).values_list("id", flat=True).first()

        batch = []
        created = 0
        for _ in range(options["count"]):
            profile_id = rng.choice(profile_ids)
            if rng.random() < 0.8:
                action, section, fields = rng.choice(MEMBER_EVENTS)
                picked = rng.sample(fields, k=min(len(fields), rng.randint(1, 3))) if fields else []
                event = AuditEvent(
                    actor_id=profile_users[profile_id],
                    actor_role=ActorRole.USER,
                    action=action,
                    profile_id=profile_id,
                    changed_fields=sorted(picked),
                    metadata={"section": section},
                )
            else:
                action = rng.choice(ADMIN_ACTIONS)
                event = AuditEvent(
                    actor_id=admin_id,
                    actor_role=ActorRole.ADMIN,
                    action=action,
                    profile_id=None if action == AuditAction.ADMIN_SEARCH_PERFORMED else profile_id,
                    metadata=admin_metadata(rng, action),
                )
            batch.append(event)

            if len(batch) >= BATCH_SIZE:
                AuditEvent.objects.bulk_create(batch)
                created += len(batch)
                batch = []

        if batch:
            AuditEvent.objects.bulk_create(batch)
            created += len(batch)

        self.stdout.write(self.style.SUCCESS(f"Created {created} synthetic audit events."))
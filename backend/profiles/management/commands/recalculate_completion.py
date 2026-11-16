from django.core.management.base import BaseCommand

from profiles.models import Demographics, HealthProfile, WellnessPreferences
from profiles.services import completion_for


class Command(BaseCommand):
    help = "Recalculate stored completion for every profile (and create any missing sections)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report what would change without saving.")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        profiles = HealthProfile.objects.prefetch_related("demographics", "wellness", "emergency_contacts")

        changed = []
        created_sections = 0

        for profile in profiles.iterator(chunk_size=500):
            if getattr(profile, "demographics", None) is None:
                created_sections += 1
                if not dry_run:
                    Demographics.objects.create(profile_id=profile.pk)
            if getattr(profile, "wellness", None) is None:
                created_sections += 1
                if not dry_run:
                    WellnessPreferences.objects.create(profile_id=profile.pk)

            result = completion_for(profile)
            if (profile.completion_percent, profile.completion_status) != (result.percent, result.status):
                profile.completion_percent = result.percent
                profile.completion_status = result.status
                changed.append(profile)

        if changed and not dry_run:
            HealthProfile.objects.bulk_update(
                changed,
                ["completion_percent", "completion_status"],
                batch_size=500,
            )

        prefix = "Would update" if dry_run else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix} {len(changed)} profile(s); "
                f"{'would create' if dry_run else 'created'} {created_sections} missing section(s)."
            )
        )

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Count

from audit.models import TIMELINE_INDEX_NAME, AuditEvent


class Command(BaseCommand):
    help = "Print the PostgreSQL execution plan for one profile's audit timeline."

    def add_arguments(self, parser):
        parser.add_argument("--profile-id", type=int, help="Defaults to the profile with the most events.")
        parser.add_argument("--without-index", action="store_true")

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("This command needs PostgreSQL.")

        profile_id = options["profile_id"] or (
            AuditEvent.objects.exclude(profile_id=None)
            .values("profile_id")
            .annotate(total=Count("id"))
            .order_by("-total")
            .values_list("profile_id", flat=True)
            .first()
        )
        if profile_id is None:
            raise CommandError("There are no audit events yet. Run: python manage.py seed_audit_events")

        queryset = AuditEvent.objects.filter(profile_id=profile_id).order_by("-id")[:20]

        if options["without_index"]:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(f'DROP INDEX "{TIMELINE_INDEX_NAME}"')
                plan = queryset.explain(analyze=True)
                transaction.set_rollback(True)
            label = f"WITHOUT index {TIMELINE_INDEX_NAME} (dropped temporarily, then rolled back)"
        else:
            plan = queryset.explain(analyze=True)
            label = f"WITH index {TIMELINE_INDEX_NAME}"

        self.stdout.write(f"Query: audit events for profile {profile_id}, newest first, first 20 rows")
        self.stdout.write(label)
        self.stdout.write("")
        self.stdout.write(plan)
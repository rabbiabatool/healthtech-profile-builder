from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from profiles.models import HealthProfile, ProfileStatus
from profiles.queries import admin_profile_queryset


class Command(BaseCommand):
    help = "Print the PostgreSQL execution plan for the admin profile list query."

    def add_arguments(self, parser):
        parser.add_argument("--status", default="ACTIVE", choices=ProfileStatus.values)
        parser.add_argument("--without-index", action="store_true")

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("This command needs PostgreSQL.")

        queryset = admin_profile_queryset(status=options["status"])[:20]
        index_name = HealthProfile._meta.indexes[0].name

        if options["without_index"]:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(f'DROP INDEX "{index_name}"')
                plan = queryset.explain(analyze=True)
                transaction.set_rollback(True)
            label = f"WITHOUT index {index_name} (dropped temporarily, then rolled back)"
        else:
            plan = queryset.explain(analyze=True)
            label = f"WITH index {index_name}"

        self.stdout.write(f"Query: status={options['status']}, newest first, first 20 rows")
        self.stdout.write(label)
        self.stdout.write("")
        self.stdout.write(plan)
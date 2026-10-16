import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from accounts.models import User


class Command(BaseCommand):
    help = "Create an administrator account. Admins cannot self-register."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--full-name", required=True)

    def handle(self, *args, **options):
        email = options["email"].strip().lower()

        try:
            validate_email(email)
        except ValidationError:
            raise CommandError("That is not a valid email address.")

        if User.objects.filter(email=email).exists():
            raise CommandError("An account with this email already exists.")

        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Password (again): ")
        if password != confirm:
            raise CommandError("Passwords do not match.")

        try:
            validate_password(password)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages))

        User.objects.create_admin(
            email=email,
            password=password,
            full_name=options["full_name"],
        )
        self.stdout.write(self.style.SUCCESS(f"Admin {email} created."))
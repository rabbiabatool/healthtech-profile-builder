import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction

from accounts.models import Role, User
from profiles.models import HealthProfile, ProfileStatus

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng!Pass#2026"


def make_user(email="sara@example.com"):
    return User.objects.create_user(email=email, password=PASSWORD, full_name="Sara Demo")


def test_password_is_hashed_not_stored_in_plain_text():
    user = make_user()
    assert user.password != PASSWORD
    assert user.check_password(PASSWORD)


def test_email_is_normalized_to_lowercase():
    user = make_user(email="Sara@Example.COM")
    assert user.email == "sara@example.com"


def test_duplicate_email_is_rejected_ignoring_case():
    make_user(email="sara@example.com")
    with pytest.raises(IntegrityError), transaction.atomic():
        make_user(email="SARA@example.com")


def test_database_itself_rejects_uppercase_email():
    user = make_user()
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=user.pk).update(email="SARA@EXAMPLE.COM")


def test_regular_user_has_no_special_powers():
    user = make_user()
    assert user.role == Role.USER
    assert not user.is_staff
    assert not user.is_superuser
    assert not user.is_admin


def test_create_admin_sets_admin_role():
    admin = User.objects.create_admin(
        email="boss@example.com", password=PASSWORD, full_name="Admin Demo"
    )
    assert admin.role == Role.ADMIN
    assert admin.is_staff
    assert admin.is_admin


def test_database_rejects_invalid_role():
    user = make_user()
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=user.pk).update(role="SUPERHERO")


def test_user_can_have_only_one_profile():
    user = make_user()
    HealthProfile.objects.create(user=user)
    with pytest.raises(IntegrityError), transaction.atomic():
        HealthProfile.objects.create(user=user)


def test_deleting_user_deletes_their_profile():
    user = make_user()
    HealthProfile.objects.create(user=user)
    user.delete()
    assert HealthProfile.objects.count() == 0


def test_negative_height_is_rejected():
    user = make_user()
    with pytest.raises(IntegrityError), transaction.atomic():
        HealthProfile.objects.create(user=user, height_cm=-5)


def test_new_profile_defaults_to_active():
    profile = HealthProfile.objects.create(user=make_user())
    assert profile.status == ProfileStatus.ACTIVE


def test_create_admin_command_creates_admin(monkeypatch):
    monkeypatch.setattr("getpass.getpass", lambda prompt="": PASSWORD)
    call_command("create_admin", email="Boss@Example.com", full_name="Admin Demo")
    admin = User.objects.get(email="boss@example.com")
    assert admin.role == Role.ADMIN
    assert admin.check_password(PASSWORD)


def test_create_admin_command_rejects_weak_password(monkeypatch):
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "123")
    with pytest.raises(CommandError):
        call_command("create_admin", email="boss@example.com", full_name="Admin Demo")
    assert not User.objects.filter(email="boss@example.com").exists()


def test_seed_data_is_idempotent():
    call_command("seed_data", count=5)
    call_command("seed_data", count=5)
    assert User.objects.count() == 5
    assert HealthProfile.objects.count() == 5
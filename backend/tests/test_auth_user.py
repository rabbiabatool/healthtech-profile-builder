from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from accounts.models import Role, User
from profiles.models import HealthProfile

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng!Pass#2026"
SIGNUP_URL = "/api/auth/signup"
REFRESH_URL = "/api/auth/refresh"
LOGOUT_URL = "/api/auth/user/logout"
ME_URL = "/api/profiles/me"


def signup_payload(**overrides):
    payload = {"full_name": "Sara Demo", "email": "sara@example.com", "password": PASSWORD}
    payload.update(overrides)
    return payload


# ---------- signup ----------


def test_signup_creates_user_and_profile(api_client):
    response = api_client.post(SIGNUP_URL, signup_payload(), format="json")
    assert response.status_code == 201
    assert response.json()["email"] == "sara@example.com"
    assert "password" not in response.json()

    user = User.objects.get(email="sara@example.com")
    assert user.role == Role.USER
    assert HealthProfile.objects.filter(user=user).exists()
    assert user.password != PASSWORD
    assert user.password.startswith("pbkdf2_sha256$")


def test_signup_lowercases_email(api_client):
    api_client.post(SIGNUP_URL, signup_payload(email="Sara@Example.COM"), format="json")
    assert User.objects.filter(email="sara@example.com").exists()


def test_signup_rejects_duplicate_email_ignoring_case(api_client, user):
    response = api_client.post(SIGNUP_URL, signup_payload(email="SARA@example.com"), format="json")
    assert response.status_code == 400
    assert "email" in response.json()
    assert User.objects.count() == 1


@pytest.mark.parametrize("email", ["not-an-email", "missing@", "", "a b@example.com"])
def test_signup_rejects_invalid_email(api_client, email):
    response = api_client.post(SIGNUP_URL, signup_payload(email=email), format="json")
    assert response.status_code == 400
    assert "email" in response.json()


@pytest.mark.parametrize("password", ["short1!", "12345678", "password", ""])
def test_signup_rejects_weak_password(api_client, password):
    response = api_client.post(SIGNUP_URL, signup_payload(password=password), format="json")
    assert response.status_code == 400
    assert "password" in response.json()
    assert User.objects.count() == 0


@pytest.mark.parametrize("missing", ["full_name", "email", "password"])
def test_signup_requires_all_fields(api_client, missing):
    payload = signup_payload()
    payload.pop(missing)
    response = api_client.post(SIGNUP_URL, payload, format="json")
    assert response.status_code == 400
    assert missing in response.json()


def test_signup_cannot_create_an_admin(api_client):
    payload = signup_payload(role="ADMIN", is_staff=True, is_superuser=True)
    response = api_client.post(SIGNUP_URL, payload, format="json")
    assert response.status_code == 201
    created = User.objects.get(email="sara@example.com")
    assert created.role == Role.USER
    assert not created.is_staff
    assert not created.is_superuser


def test_csrf_endpoint_sets_cookie_and_returns_token(api_client):
    response = api_client.get("/api/auth/csrf")
    assert response.status_code == 200
    assert response.json()["csrfToken"]
    assert "csrftoken" in api_client.cookies


# ---------- login ----------


def test_login_sets_httponly_cookies_and_returns_no_tokens(api_client, user, login):
    response = login(api_client)
    assert response.status_code == 200

    body = response.json()
    assert body["user"]["email"] == "sara@example.com"
    assert "access" not in body
    assert "refresh" not in body

    access = api_client.cookies["access_token"]
    refresh = api_client.cookies["refresh_token"]
    assert access["httponly"]
    assert refresh["httponly"]
    assert access["samesite"] == "Lax"
    assert access["path"] == "/"
    assert refresh["path"] == "/api/auth/"


def test_login_email_is_case_insensitive(api_client, user, login):
    assert login(api_client, email="SARA@Example.com").status_code == 200


def test_login_with_wrong_password_fails(api_client, user, login):
    response = login(api_client, password="Wrong!Pass#999")
    assert response.status_code == 401
    assert "access_token" not in api_client.cookies


def test_login_does_not_reveal_whether_email_exists(api_client, user, login):
    wrong_password = login(api_client, password="Wrong!Pass#999")
    unknown_email = login(api_client, email="nobody@example.com")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_admin_cannot_use_the_user_login(api_client, admin, login):
    response = login(api_client, email="boss@example.com")
    assert response.status_code == 401
    assert "access_token" not in api_client.cookies


def test_inactive_user_cannot_login(api_client, user, login):
    user.is_active = False
    user.save()
    assert login(api_client).status_code == 401


def test_jwt_claims_contain_no_secrets(api_client, user, login):
    login(api_client)
    payload = AccessToken(api_client.cookies["access_token"].value).payload
    assert set(payload) == {"token_type", "exp", "iat", "jti", "user_id"}
    assert user.password not in str(payload)


# ---------- token validation ----------


def test_request_without_token_is_rejected(api_client):
    assert api_client.get(ME_URL).status_code == 401


def test_expired_access_token_is_rejected(api_client, user):
    token = AccessToken.for_user(user)
    token.set_exp(from_time=timezone.now() - timedelta(hours=1), lifetime=timedelta(minutes=10))
    api_client.cookies["access_token"] = str(token)
    assert api_client.get(ME_URL).status_code == 401


def test_tampered_token_is_rejected(api_client, user, login):
    login(api_client)
    header, payload, signature = api_client.cookies["access_token"].value.split(".")
    api_client.cookies["access_token"] = f"{header}.{payload}.{'A' * len(signature)}"
    assert api_client.get(ME_URL).status_code == 401


def test_refresh_token_cannot_be_used_as_access_token(api_client, user):
    api_client.cookies["access_token"] = str(RefreshToken.for_user(user))
    assert api_client.get(ME_URL).status_code == 401


def test_token_of_deleted_user_is_rejected(api_client, user, login):
    login(api_client)
    user.delete()
    assert api_client.get(ME_URL).status_code == 401


# ---------- refresh and logout ----------


def test_refresh_rotates_tokens_and_kills_the_old_one(api_client, user, login):
    login(api_client)
    old_refresh = api_client.cookies["refresh_token"].value

    response = api_client.post(REFRESH_URL)
    assert response.status_code == 200
    assert api_client.cookies["refresh_token"].value != old_refresh

    api_client.cookies["refresh_token"] = old_refresh
    assert api_client.post(REFRESH_URL).status_code == 401


def test_refresh_without_cookie_is_rejected(api_client):
    assert api_client.post(REFRESH_URL).status_code == 401


def test_refresh_is_rejected_for_deactivated_user(api_client, user, login):
    login(api_client)
    user.is_active = False
    user.save()
    assert api_client.post(REFRESH_URL).status_code == 401


def test_logout_clears_cookies_and_revokes_refresh_token(api_client, user, login):
    login(api_client)
    old_refresh = api_client.cookies["refresh_token"].value

    assert api_client.post(LOGOUT_URL).status_code == 204
    assert api_client.get(ME_URL).status_code == 401

    api_client.cookies["refresh_token"] = old_refresh
    assert api_client.post(REFRESH_URL).status_code == 401


def test_logout_without_cookies_still_succeeds(api_client):
    assert api_client.post(LOGOUT_URL).status_code == 204


def test_logout_requires_csrf_token_in_browser_mode(csrf_client, user, login, csrf_header):
    login(csrf_client)
    assert csrf_client.post(LOGOUT_URL).status_code == 403
    response = csrf_client.post(LOGOUT_URL, **csrf_header(csrf_client))
    assert response.status_code == 204
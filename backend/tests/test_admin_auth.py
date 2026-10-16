from datetime import timedelta

import pytest
from django.contrib.sessions.models import Session
from django.utils import timezone

from accounts.models import Role, User
from profiles.models import HealthProfile

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng!Pass#2026"
ADMIN_LOGIN_URL = "/api/admin/login"
ADMIN_ME_URL = "/api/admin/me"
ADMIN_LOGOUT_URL = "/api/admin/logout"


def test_admin_csrf_endpoint_sets_cookie(api_client):
    response = api_client.get("/api/admin/csrf")
    assert response.status_code == 200
    assert response.json()["csrfToken"]
    assert "csrftoken" in api_client.cookies


def test_admin_login_creates_a_secure_session_cookie(api_client, admin, admin_login):
    response = admin_login(api_client)
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "ADMIN"
    assert "password" not in response.content.decode()

    cookie = api_client.cookies["admin_session"]
    assert cookie["httponly"]
    assert cookie["samesite"] == "Lax"
    assert cookie["max-age"] == 3600
    assert Session.objects.count() == 1
    assert "access_token" not in api_client.cookies
    assert "refresh_token" not in api_client.cookies


def test_admin_login_requires_csrf_token(csrf_client, admin):
    response = csrf_client.post(
        ADMIN_LOGIN_URL,
        {"email": "boss@example.com", "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 403
    assert "admin_session" not in csrf_client.cookies


def test_admin_login_with_wrong_password_fails(api_client, admin, admin_login):
    response = admin_login(api_client, password="Wrong!Pass#999")
    assert response.status_code == 401
    assert "admin_session" not in api_client.cookies


def test_standard_user_cannot_get_an_admin_session(api_client, user, admin_login):
    response = admin_login(api_client, email="sara@example.com")
    assert response.status_code == 401
    assert "admin_session" not in api_client.cookies
    assert Session.objects.count() == 0


def test_inactive_admin_cannot_login(api_client, admin, admin_login):
    admin.is_active = False
    admin.save()
    assert admin_login(api_client).status_code == 401


@pytest.mark.parametrize(
    "url",
    ["/api/admin/signup", "/api/admin/register", "/api/auth/admin/signup"],
)
def test_there_is_no_public_admin_signup(api_client, url):
    payload = {"email": "evil@example.com", "password": PASSWORD, "full_name": "Evil"}
    assert api_client.post(url, payload, format="json").status_code == 404
    assert not User.objects.filter(email="evil@example.com").exists()


def test_admin_me_works_with_a_session(admin_client):
    response = admin_client.get(ADMIN_ME_URL)
    assert response.status_code == 200
    assert response.json()["email"] == "boss@example.com"


def test_admin_me_without_a_session_is_rejected(api_client):
    assert api_client.get(ADMIN_ME_URL).status_code == 401


def test_logout_destroys_the_session(admin_client):
    assert Session.objects.count() == 1
    assert admin_client.post(ADMIN_LOGOUT_URL).status_code == 204
    assert Session.objects.count() == 0
    assert admin_client.get(ADMIN_ME_URL).status_code == 401


def test_logout_requires_csrf_token_in_browser_mode(csrf_client, admin, admin_login, csrf_header):
    admin_login(csrf_client)
    assert csrf_client.post(ADMIN_LOGOUT_URL).status_code == 403
    assert csrf_client.get(ADMIN_ME_URL).status_code == 200

    response = csrf_client.post(ADMIN_LOGOUT_URL, **csrf_header(csrf_client))
    assert response.status_code == 204


def test_expired_session_is_rejected(admin_client):
    assert admin_client.get(ADMIN_ME_URL).status_code == 200
    Session.objects.update(expire_date=timezone.now() - timedelta(minutes=1))
    assert admin_client.get(ADMIN_ME_URL).status_code == 401


def test_forged_session_cookie_is_rejected(api_client, admin):
    api_client.cookies["admin_session"] = "this-is-not-a-real-session-id"
    assert api_client.get(ADMIN_ME_URL).status_code == 401


@pytest.mark.parametrize(
    "method, url",
    [
        ("get", "/api/admin/me"),
        ("get", "/api/admin/profiles"),
        ("get", "/api/admin/profiles/1"),
        ("patch", "/api/admin/profiles/1/deactivate"),
    ],
)
def test_user_jwt_does_not_grant_admin_access(api_client, user, login, method, url):
    login(api_client)
    response = getattr(api_client, method)(url)
    assert response.status_code == 401


def test_client_side_claims_do_not_grant_admin_access(api_client, user, login):
    login(api_client)
    api_client.cookies["role"] = "ADMIN"
    api_client.cookies["is_admin"] = "true"
    response = api_client.get(
        "/api/admin/profiles",
        HTTP_X_ROLE="ADMIN",
        HTTP_X_IS_ADMIN="true",
    )
    assert response.status_code == 401


def test_admin_session_cannot_use_user_endpoints(admin_client):
    assert admin_client.get("/api/profiles/me").status_code == 401


def test_demoting_an_admin_takes_effect_immediately(admin_client, admin):
    assert admin_client.get(ADMIN_ME_URL).status_code == 200
    User.objects.filter(pk=admin.pk).update(role=Role.USER)
    assert admin_client.get(ADMIN_ME_URL).status_code == 403
    assert admin_client.get("/api/admin/profiles").status_code == 403
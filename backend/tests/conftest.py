import pytest
from rest_framework.test import APIClient

from accounts.models import User
from profiles.models import HealthProfile

PASSWORD = "Str0ng!Pass#2026"


def _make_user(email, full_name):
    user = User.objects.create_user(email=email, password=PASSWORD, full_name=full_name)
    HealthProfile.objects.create(user=user)
    return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def csrf_client():
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def user(db):
    return _make_user("sara@example.com", "Sara Demo")


@pytest.fixture
def other_user(db):
    return _make_user("omar@example.com", "Omar Demo")


@pytest.fixture
def admin(db):
    return User.objects.create_admin(
        email="boss@example.com", password=PASSWORD, full_name="Admin Demo"
    )


@pytest.fixture
def login():
    def _login(client, email="sara@example.com", password=PASSWORD):
        return client.post(
            "/api/auth/user/login",
            {"email": email, "password": password},
            format="json",
        )

    return _login


@pytest.fixture
def csrf_header():
    def _header(client):
        token = client.get("/api/auth/csrf").json()["csrfToken"]
        return {"HTTP_X_CSRFTOKEN": token}

    return _header

@pytest.fixture
def admin_login():
    def _login(client, email="boss@example.com", password=PASSWORD):
        token = client.get("/api/admin/csrf").json()["csrfToken"]
        return client.post(
            "/api/admin/login",
            {"email": email, "password": password},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

    return _login


@pytest.fixture
def admin_client(admin, admin_login):
    client = APIClient()
    assert admin_login(client).status_code == 200
    return client
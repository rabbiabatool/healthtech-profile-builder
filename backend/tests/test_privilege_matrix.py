import pytest
from rest_framework.test import APIClient

from profiles.models import EmergencyContact, HealthProfile

pytestmark = pytest.mark.django_db

CALLERS = ["anonymous", "member_a", "member_b", "admin"]

MEMBER_ONLY = {"anonymous": 401, "member_a": 200, "member_b": 200, "admin": 401}
ADMIN_ONLY = {"anonymous": 401, "member_a": 401, "member_b": 401, "admin": 200}
OWNER_ONLY = {"anonymous": 401, "member_a": 200, "member_b": 404, "admin": 401}

ROUTES = [
    ("get", "/api/profiles/me", None, MEMBER_ONLY),
    ("patch", "/api/profiles/me", {"status": "INACTIVE"}, {"anonymous": 401, "member_a": 405, "member_b": 405, "admin": 401}),
    ("get", "/api/profiles/me/demographics", None, MEMBER_ONLY),
    ("patch", "/api/profiles/me/demographics", {"country": "Canada"}, MEMBER_ONLY),
    ("delete", "/api/profiles/me/demographics", None, MEMBER_ONLY),
    ("get", "/api/profiles/me/wellness", None, MEMBER_ONLY),
    ("patch", "/api/profiles/me/wellness", {"activity_level": "LIGHT"}, MEMBER_ONLY),
    ("delete", "/api/profiles/me/wellness", None, MEMBER_ONLY),
    ("get", "/api/profiles/me/emergency-contacts", None, MEMBER_ONLY),
    (
        "post",
        "/api/profiles/me/emergency-contacts",
        {"name": "Fictional Helper", "relationship": "FRIEND", "phone": "555-0150"},
        {"anonymous": 401, "member_a": 201, "member_b": 201, "admin": 401},
    ),
    ("get", "/api/profiles/me/emergency-contacts/{contact_id}", None, OWNER_ONLY),
    ("patch", "/api/profiles/me/emergency-contacts/{contact_id}", {"name": "Updated Contact"}, OWNER_ONLY),
    (
        "delete",
        "/api/profiles/me/emergency-contacts/{contact_id}",
        None,
        {"anonymous": 401, "member_a": 204, "member_b": 404, "admin": 401},
    ),
    ("get", "/api/admin/me", None, ADMIN_ONLY),
    ("get", "/api/admin/profiles", None, ADMIN_ONLY),
    ("get", "/api/admin/profiles/{profile_id}", None, ADMIN_ONLY),
    ("patch", "/api/admin/profiles/{profile_id}/deactivate", None, ADMIN_ONLY),
    ("patch", "/api/admin/profiles/{profile_id}/reactivate", None, ADMIN_ONLY),
    ("get", "/api/admin/audit-events", None, ADMIN_ONLY),
    ("get", "/api/admin/profiles/{profile_id}/audit-events", None, ADMIN_ONLY),
]

FORBIDDEN_KEYS = {"password", "is_staff", "is_superuser", "last_login", "groups", "user_permissions", "role", "token"}


def call(client, method, url, body=None):
    send = getattr(client, method)
    if method in ("post", "patch", "put"):
        return send(url, body if body is not None else {}, format="json")
    return send(url)


def collect_keys(value):
    keys = set()
    if isinstance(value, dict):
        for key, inner in value.items():
            keys.add(key)
            keys |= collect_keys(inner)
    elif isinstance(value, list):
        for item in value:
            keys |= collect_keys(item)
    return keys


@pytest.fixture
def world(user, other_user, admin, login, admin_login):
    member_a = APIClient()
    member_b = APIClient()
    admin_client = APIClient()
    assert login(member_a, "sara@example.com").status_code == 200
    assert login(member_b, "omar@example.com").status_code == 200
    assert admin_login(admin_client).status_code == 200

    profile_a = HealthProfile.objects.get(user=user)
    contact_a = EmergencyContact.objects.create(
        profile=profile_a, name="Fictional Contact", phone="555-0101", is_primary=True
    )
    return {
        "clients": {
            "anonymous": APIClient(),
            "member_a": member_a,
            "member_b": member_b,
            "admin": admin_client,
        },
        "ids": {"profile_id": profile_a.pk, "contact_id": contact_a.pk},
    }


@pytest.mark.parametrize("caller", CALLERS)
@pytest.mark.parametrize(
    "method, path, body, expected",
    ROUTES,
    ids=[f"{route[0].upper()} {route[1]}" for route in ROUTES],
)
def test_route_matrix(world, method, path, body, expected, caller):
    url = path.format(**world["ids"])
    response = call(world["clients"][caller], method, url, body)
    assert response.status_code == expected[caller], f"{caller} {method.upper()} {url}"


@pytest.mark.parametrize(
    "caller, path",
    [
        ("member_a", "/api/profiles/me"),
        ("member_a", "/api/profiles/me/demographics"),
        ("member_a", "/api/profiles/me/wellness"),
        ("member_a", "/api/profiles/me/emergency-contacts"),
        ("member_a", "/api/profiles/me/emergency-contacts/{contact_id}"),
        ("admin", "/api/admin/profiles"),
        ("admin", "/api/admin/profiles/{profile_id}"),
    ],
)
def test_responses_never_contain_sensitive_keys(world, caller, path):
    response = world["clients"][caller].get(path.format(**world["ids"]))
    assert response.status_code == 200
    assert collect_keys(response.json()) & FORBIDDEN_KEYS == set()


@pytest.mark.parametrize(
    "method, path",
    [
        ("patch", "/api/admin/profiles/{profile_id}"),
        ("delete", "/api/admin/profiles/{profile_id}"),
        ("post", "/api/admin/profiles/{profile_id}/demographics"),
    ],
)
def test_admin_has_no_route_to_edit_patient_data(world, method, path):
    response = call(world["clients"]["admin"], method, path.format(**world["ids"]), {"country": "Canada"})
    assert response.status_code in (404, 405)
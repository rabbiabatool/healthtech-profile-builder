import re

import pytest
from django.core.management import call_command
from drf_spectacular.generators import SchemaGenerator

pytestmark = pytest.mark.django_db

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
CSRF_EXEMPT = {("/api/auth/signup", "post")}

EXPECTED_OPERATIONS = {
    ("/api/auth/csrf", "get"),
    ("/api/auth/signup", "post"),
    ("/api/auth/user/login", "post"),
    ("/api/auth/refresh", "post"),
    ("/api/auth/user/logout", "post"),
    ("/api/profiles/me", "get"),
    ("/api/profiles/me", "post"),
    ("/api/profiles/me", "delete"),
    ("/api/profiles/me/demographics", "get"),
    ("/api/profiles/me/demographics", "patch"),
    ("/api/profiles/me/demographics", "delete"),
    ("/api/profiles/me/wellness", "get"),
    ("/api/profiles/me/wellness", "patch"),
    ("/api/profiles/me/wellness", "delete"),
    ("/api/profiles/me/emergency-contacts", "get"),
    ("/api/profiles/me/emergency-contacts", "post"),
    ("/api/profiles/me/emergency-contacts/{}", "get"),
    ("/api/profiles/me/emergency-contacts/{}", "patch"),
    ("/api/profiles/me/emergency-contacts/{}", "delete"),
    ("/api/admin/csrf", "get"),
    ("/api/admin/login", "post"),
    ("/api/admin/logout", "post"),
    ("/api/admin/me", "get"),
    ("/api/admin/profiles", "get"),
    ("/api/admin/profiles/{}", "get"),
    ("/api/admin/profiles/{}/deactivate", "patch"),
    ("/api/admin/profiles/{}/reactivate", "patch"),
    ("/api/admin/audit-events", "get"),
    ("/api/admin/profiles/{}/audit-events", "get"),
}


def normalize(path):
    return re.sub(r"\{[^}]+\}", "{}", path)


@pytest.fixture(scope="module")
def schema():
    return SchemaGenerator().get_schema(request=None, public=True)


@pytest.fixture(scope="module")
def operations(schema):
    return {
        (normalize(path), method): operation
        for path, item in schema["paths"].items()
        for method, operation in item.items()
        if method in HTTP_METHODS
    }


def test_every_public_endpoint_is_documented(operations):
    missing = EXPECTED_OPERATIONS - set(operations)
    assert not missing, f"Undocumented operations: {sorted(missing)}"


def test_every_operation_has_a_summary_and_a_tag(operations):
    for key, operation in operations.items():
        assert operation.get("summary"), f"{key} has no summary"
        assert operation.get("tags"), f"{key} has no tag"


def test_state_changing_operations_document_the_csrf_header(operations):
    for (path, method), operation in operations.items():
        if method == "get" or (path, method) in CSRF_EXEMPT:
            continue
        headers = {p["name"] for p in operation.get("parameters", []) if p.get("in") == "header"}
        assert "X-CSRFToken" in headers, f"{method.upper()} {path} does not document the CSRF header"


def test_the_two_cookie_sign_in_schemes_are_documented(schema, operations):
    schemes = schema["components"]["securitySchemes"]
    assert schemes["memberJwtCookie"]["in"] == "cookie"
    assert schemes["adminSessionCookie"]["in"] == "cookie"

    member_security = {name for req in operations[("/api/profiles/me", "get")]["security"] for name in req}
    admin_security = {name for req in operations[("/api/admin/me", "get")]["security"] for name in req}
    assert "memberJwtCookie" in member_security
    assert "adminSessionCookie" in admin_security


def test_passwords_only_appear_in_request_bodies(schema):
    for name, component in schema["components"]["schemas"].items():
        if "password" in component.get("properties", {}):
            assert name.endswith("Request"), f"{name} exposes a password field"


def test_the_audit_log_is_documented_as_read_only(operations):
    audit_methods = {method for (path, method) in operations if "audit-events" in path}
    assert audit_methods == {"get"}


def test_the_schema_file_can_be_generated_and_validates(tmp_path):
    target = tmp_path / "openapi.yaml"
    call_command("spectacular", file=str(target), validate=True)
    assert target.stat().st_size > 1000


@pytest.mark.parametrize("url", ["/api/docs/", "/api/redoc/", "/api/schema/"])
def test_interactive_docs_are_not_served_when_debug_is_off(api_client, url):
    assert api_client.get(url).status_code == 404
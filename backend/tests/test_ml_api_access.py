import pytest
from rest_framework.test import APIClient

from mlcore import config
from predictions.tests.model_fixtures import artifact_dir, model_ready, no_model  # noqa: F401
from predictions.tests.samples import VALID, changed

pytestmark = pytest.mark.django_db

PREDICT_URL = "/api/v1/ml/no-show/predict"
MODEL_URL = "/api/v1/ml/model"
CALLERS = ["anonymous", "member_a", "member_b", "admin"]

ALLOWED = {"anonymous": 401, "member_a": 200, "member_b": 200, "admin": 200}
BAD_INPUT = {"anonymous": 401, "member_a": 400, "member_b": 400, "admin": 400}
NOT_ALLOWED_METHOD = {"anonymous": 401, "member_a": 405, "member_b": 405, "admin": 405}

ROUTES = [
    ("model info", "get", MODEL_URL, None, ALLOWED),
    ("valid prediction", "post", PREDICT_URL, VALID, ALLOWED),
    ("invalid prediction", "post", PREDICT_URL, changed(age=17), BAD_INPUT),
    ("GET on predict", "get", PREDICT_URL, None, NOT_ALLOWED_METHOD),
    ("PUT on predict", "put", PREDICT_URL, VALID, NOT_ALLOWED_METHOD),
    ("DELETE on predict", "delete", PREDICT_URL, None, NOT_ALLOWED_METHOD),
    ("POST on model info", "post", MODEL_URL, {}, NOT_ALLOWED_METHOD),
    ("PATCH on model info", "patch", MODEL_URL, {}, NOT_ALLOWED_METHOD),
]

FORBIDDEN_KEYS = {
    "password", "is_staff", "is_superuser", "last_login", "groups",
    "user_permissions", "role", "token", "artifact_sha256", "library_versions",
}


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
def world(user, other_user, admin, login, admin_login, model_ready):
    member_a = APIClient()
    member_b = APIClient()
    admin_client = APIClient()
    assert login(member_a, "sara@example.com").status_code == 200
    assert login(member_b, "omar@example.com").status_code == 200
    assert admin_login(admin_client).status_code == 200
    return {
        "anonymous": APIClient(),
        "member_a": member_a,
        "member_b": member_b,
        "admin": admin_client,
    }


@pytest.mark.parametrize("caller", CALLERS)
@pytest.mark.parametrize(
    "label, method, url, body, expected", ROUTES, ids=[route[0] for route in ROUTES]
)
def test_ml_route_matrix(world, label, method, url, body, expected, caller):
    response = call(world[caller], method, url, body)
    assert response.status_code == expected[caller], f"{caller}: {label}"


def test_members_and_admins_get_the_documented_response(world):
    for caller in ("member_a", "member_b", "admin"):
        data = world[caller].post(PREDICT_URL, VALID, format="json").json()
        assert set(data) == {
            "model_version", "schema_version", "probability", "risk_band",
            "threshold", "input_warnings", "disclaimer",
        }
        assert data["disclaimer"] == config.DISCLAIMER


def test_the_answer_does_not_depend_on_who_asks(world):
    answers = [world[caller].post(PREDICT_URL, VALID, format="json").json() for caller in ("member_a", "member_b", "admin")]
    assert answers[0] == answers[1] == answers[2]


@pytest.mark.parametrize("caller, method, url", [
    ("member_a", "get", MODEL_URL),
    ("admin", "get", MODEL_URL),
    ("member_a", "post", PREDICT_URL),
    ("admin", "post", PREDICT_URL),
])
def test_responses_never_contain_sensitive_keys(world, caller, method, url):
    response = call(world[caller], method, url, VALID if method == "post" else None)
    assert response.status_code == 200
    assert collect_keys(response.json()) & FORBIDDEN_KEYS == set()


def test_admin_session_needs_a_csrf_token_to_predict(csrf_client, admin, admin_login, csrf_header, model_ready):
    admin_login(csrf_client)
    assert csrf_client.post(PREDICT_URL, VALID, format="json").status_code == 403
    response = csrf_client.post(PREDICT_URL, VALID, format="json", **csrf_header(csrf_client))
    assert response.status_code == 200


def test_member_cookie_login_needs_a_csrf_token_to_predict(csrf_client, user, login, csrf_header, model_ready):
    assert login(csrf_client).status_code == 200
    assert csrf_client.post(PREDICT_URL, VALID, format="json").status_code == 403
    response = csrf_client.post(PREDICT_URL, VALID, format="json", **csrf_header(csrf_client))
    assert response.status_code == 200


def test_signed_in_callers_get_503_when_the_model_is_missing(user, login, no_model):
    client = APIClient()
    assert login(client).status_code == 200
    assert client.get(MODEL_URL).status_code == 503
    assert client.post(PREDICT_URL, VALID, format="json").status_code == 503
    assert client.post(PREDICT_URL, changed(age=17), format="json").status_code == 400
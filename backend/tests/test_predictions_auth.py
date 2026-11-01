import pytest
from rest_framework_simplejwt.tokens import RefreshToken

from predictions.tests.conftest import artifact_dir, model_ready  # noqa: F401
from predictions.tests.samples import VALID

pytestmark = pytest.mark.django_db

MODEL_URL = "/api/v1/ml/model"
PREDICT_URL = "/api/v1/ml/no-show/predict"


def test_member_can_get_model_info(api_client, user, login, model_ready):
    login(api_client)
    response = api_client.get(MODEL_URL)
    assert response.status_code == 200
    data = response.json()
    assert "input_schema" in data
    assert "disclaimer" in data
    assert "threshold" in data


def test_member_can_post_predict_with_csrf(api_client, user, login, csrf_header, model_ready):
    login(api_client)
    headers = csrf_header(api_client)
    response = api_client.post(PREDICT_URL, VALID, format="json", **headers)
    assert response.status_code == 200
    data = response.json()
    assert 0.0 <= data["probability"] <= 1.0
    assert data["risk_band"] in {"LOW", "MEDIUM", "HIGH"}
    assert "model_version" in data


def test_member_predict_enforces_csrf(csrf_client, user, login, model_ready):
    login(csrf_client)
    # Missing X-CSRFToken header on unsafe method POST
    response = csrf_client.post(PREDICT_URL, VALID, format="json")
    assert response.status_code == 403
    assert "CSRF" in response.json().get("detail", "")


def test_admin_session_cannot_get_model_info(admin_client, model_ready):
    # Admin session authentication is not accepted on member prediction routes
    response = admin_client.get(MODEL_URL)
    assert response.status_code == 401


def test_admin_session_cannot_post_predict(admin_client, model_ready):
    response = admin_client.post(PREDICT_URL, VALID, format="json")
    assert response.status_code == 401


def test_admin_user_with_jwt_is_forbidden_by_role(api_client, admin, model_ready):
    # Even if an admin user presents a valid JWT access token, IsStandardUser blocks them
    refresh = RefreshToken.for_user(admin)
    access_token = str(refresh.access_token)
    api_client.cookies["access_token"] = access_token

    response = api_client.get(MODEL_URL)
    assert response.status_code == 403
    assert "Standard user access only" in response.json().get("detail", "")

    csrf_token = api_client.get("/api/auth/csrf").json()["csrfToken"]
    response = api_client.post(
        PREDICT_URL,
        VALID,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert response.status_code == 403
    assert "Standard user access only" in response.json().get("detail", "")


def test_anonymous_cannot_access_predictions(api_client, model_ready):
    response = api_client.get(MODEL_URL)
    assert response.status_code == 401

    response = api_client.post(PREDICT_URL, VALID, format="json")
    assert response.status_code == 401


def test_admin_predictions_url_does_not_exist(admin_client):
    # No admin predictions endpoint exists in backend routing
    response = admin_client.get("/api/admin/predictions")
    assert response.status_code == 404

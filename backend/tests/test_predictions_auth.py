import json
from pathlib import Path
import pytest
from rest_framework_simplejwt.tokens import RefreshToken

from mlcore import config, registry
pytest_plugins = ["predictions.tests.conftest"]
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


def test_malformed_metadata_returns_503_not_500_and_recovers(api_client, user, login, csrf_header, model_ready, artifact_dir):
    """Ensure malformed or non-object metadata returns documented 503 (not 500), and recovers when repaired."""
    login(api_client)
    headers = csrf_header(api_client)
    meta_path = Path(artifact_dir) / config.METADATA_FILENAME
    valid_content = meta_path.read_text(encoding="utf-8")

    try:
        # 1. Non-object metadata: JSON list []
        meta_path.write_text("[]", encoding="utf-8")
        registry.clear_cache()
        response = api_client.get(MODEL_URL)
        assert response.status_code == 503
        assert "expected a JSON object" in response.json().get("detail", "")

        post_res = api_client.post(PREDICT_URL, VALID, format="json", **headers)
        assert post_res.status_code == 503
        assert "expected a JSON object" in post_res.json().get("detail", "")

        # 2. Non-object metadata: JSON null
        meta_path.write_text("null", encoding="utf-8")
        registry.clear_cache()
        response = api_client.get(MODEL_URL)
        assert response.status_code == 503
        assert "expected a JSON object" in response.json().get("detail", "")

        # 3. Missing required field (e.g. threshold deleted)
        valid_json = json.loads(valid_content)
        bad_json = dict(valid_json)
        del bad_json["threshold"]
        meta_path.write_text(json.dumps(bad_json), encoding="utf-8")
        registry.clear_cache()
        response = api_client.get(MODEL_URL)
        assert response.status_code == 503
        assert "missing required field" in response.json().get("detail", "")

        # 4. Recovery: restore valid metadata and verify 200 without restart
        meta_path.write_text(valid_content, encoding="utf-8")
        registry.clear_cache()
        recovery_get = api_client.get(MODEL_URL)
        assert recovery_get.status_code == 200
        assert "input_schema" in recovery_get.json()

        recovery_post = api_client.post(PREDICT_URL, VALID, format="json", **headers)
        assert recovery_post.status_code == 200
        assert "probability" in recovery_post.json()

    finally:
        meta_path.write_text(valid_content, encoding="utf-8")
        registry.clear_cache()

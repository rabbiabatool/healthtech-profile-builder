from types import SimpleNamespace

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from mlcore import config
from predictions import views
from predictions.tests.samples import VALID, changed

factory = APIRequestFactory()
PREDICT_URL = "/api/v1/ml/no-show/predict"
MODEL_URL = "/api/v1/ml/model"
MEMBER_ROLE = "USER"
ADMIN_ROLE = "ADMIN"


def _user(role):
    return SimpleNamespace(is_authenticated=True, role=role, is_active=True)


def _post(payload=None, role=MEMBER_ROLE, raw=None, format="json"):
    if raw is not None:
        request = factory.post(PREDICT_URL, raw, content_type="application/json")
    else:
        request = factory.post(PREDICT_URL, payload, format=format)
    if role is not None:
        force_authenticate(request, user=_user(role))
    return views.NoShowPredictView.as_view()(request)


def _get_model_info(role=MEMBER_ROLE):
    request = factory.get(MODEL_URL)
    if role is not None:
        force_authenticate(request, user=_user(role))
    return views.ModelInfoView.as_view()(request)


def test_members_get_a_prediction(model_ready):
    response = _post(VALID, role=MEMBER_ROLE)
    assert response.status_code == 200
    assert set(response.data) == {
        "model_version", "schema_version", "probability", "risk_band",
        "threshold", "input_warnings", "disclaimer",
    }
    assert 0.0 <= response.data["probability"] <= 1.0
    assert response.data["risk_band"] in {"LOW", "MEDIUM", "HIGH"}
    assert response.data["model_version"] == config.MODEL_VERSION
    assert response.data["disclaimer"] == config.DISCLAIMER


def test_admins_are_forbidden_from_predictions(model_ready):
    response = _post(VALID, role=ADMIN_ROLE)
    assert response.status_code == 403
    assert "Standard user access only" in str(response.data.get("detail", ""))


def test_admins_are_forbidden_from_model_info(model_ready):
    response = _get_model_info(role=ADMIN_ROLE)
    assert response.status_code == 403
    assert "Standard user access only" in str(response.data.get("detail", ""))


@pytest.mark.django_db
def test_anonymous_callers_are_refused(model_ready):
    response = _post(VALID, role=None)
    assert response.status_code in (401, 403)
    assert "probability" not in response.data


def test_unknown_roles_are_refused(model_ready):
    assert _post(VALID, role="guest").status_code == 403
    assert _get_model_info(role="guest").status_code == 403


def test_null_distance_is_accepted(model_ready):
    assert _post(changed(distance_km=None)).status_code == 200


def test_the_same_input_always_gives_the_same_answer(model_ready):
    assert _post(VALID).data == _post(VALID).data


def test_unusual_values_produce_warnings(model_ready):
    extreme = changed(lead_time_days=180, previous_appointments=60, previous_no_shows=10)
    warnings = _post(extreme).data["input_warnings"]
    assert any("lead_time_days" in note for note in warnings)


def test_bad_json_and_bad_shapes_give_400(model_ready):
    assert _post(raw='{"age": ').status_code == 400
    assert _post(raw='{"age": NaN}').status_code == 400
    assert _post(raw="[]").status_code == 400
    empty = _post(raw="{}")
    assert empty.status_code == 400
    assert "age" in empty.data


def test_validation_errors_name_the_bad_field(model_ready):
    response = _post(changed(age=17, gender="F"))
    assert response.status_code == 400
    assert "age" in response.data and "gender" in response.data


def test_form_style_bodies_are_not_accepted(model_ready):
    assert _post(VALID, format="multipart").status_code == 415


def test_wrong_http_methods_are_refused(model_ready):
    get_request = factory.get(PREDICT_URL)
    force_authenticate(get_request, user=_user(MEMBER_ROLE))
    assert views.NoShowPredictView.as_view()(get_request).status_code == 405
    post_request = factory.post(MODEL_URL, {}, format="json")
    force_authenticate(post_request, user=_user(MEMBER_ROLE))
    assert views.ModelInfoView.as_view()(post_request).status_code == 405


def test_bad_input_is_reported_even_when_the_model_is_missing(no_model):
    assert _post(changed(age=17)).status_code == 400


def test_a_missing_model_gives_503_not_a_crash(no_model):
    response = _post(VALID)
    assert response.status_code == 503
    assert "detail" in response.data
    assert _get_model_info().status_code == 503


def test_a_tampered_model_gives_503(tampered_model):
    response = _post(VALID)
    assert response.status_code == 503
    assert "integrity" in response.data["detail"]


def test_malformed_metadata_gives_503_and_recovers(artifact_dir, monkeypatch, tmp_path):
    import shutil
    from mlcore import registry

    target = tmp_path / "corrupt_meta"
    shutil.copytree(artifact_dir, target)
    meta_path = target / config.METADATA_FILENAME
    valid_text = meta_path.read_text(encoding="utf-8")

    monkeypatch.setattr(config, "ARTIFACT_DIR", target)

    # 1. Non-object metadata (list)
    meta_path.write_text("[]", encoding="utf-8")
    registry.clear_cache()
    info_res = _get_model_info()
    assert info_res.status_code == 503
    assert "JSON object" in info_res.data["detail"]

    predict_res = _post(VALID)
    assert predict_res.status_code == 503
    assert "JSON object" in predict_res.data["detail"]

    # 2. Repair metadata and verify immediate recovery
    meta_path.write_text(valid_text, encoding="utf-8")
    registry.clear_cache()
    recovery_info = _get_model_info()
    assert recovery_info.status_code == 200
    assert "input_schema" in recovery_info.data

    recovery_predict = _post(VALID)
    assert recovery_predict.status_code == 200
    assert "probability" in recovery_predict.data


def test_model_info_has_what_a_form_needs_and_hides_internals(model_ready):
    response = _get_model_info(role=MEMBER_ROLE)
    assert response.status_code == 200
    data = response.data
    assert {"input_schema", "limitations", "disclaimer", "threshold", "risk_band_cutpoints"} <= set(data)
    assert "age" in data["input_schema"]["numeric_ranges"]
    assert data["shipped_model"] == config.SHIPPED_MODEL
    assert "artifact_sha256" not in data and "library_versions" not in data

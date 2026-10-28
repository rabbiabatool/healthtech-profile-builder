import pytest
from drf_spectacular.generators import SchemaGenerator

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def schema():
    return SchemaGenerator().get_schema(request=None, public=True)


def test_the_two_ml_operations_are_fully_documented(schema):
    paths = schema["paths"]
    model_info = paths["/api/v1/ml/model"]["get"]
    predict = paths["/api/v1/ml/no-show/predict"]["post"]

    for operation in (model_info, predict):
        assert operation.get("summary")
        assert operation.get("tags")

    headers = {p["name"] for p in predict.get("parameters", []) if p.get("in") == "header"}
    assert "X-CSRFToken" in headers

    for operation in (model_info, predict):
        schemes = {name for requirement in operation["security"] for name in requirement}
        assert {"memberJwtCookie", "adminSessionCookie"} <= schemes

    for code in ("200", "400", "401", "403", "503"):
        assert code in predict["responses"]
    for code in ("200", "401", "403", "503"):
        assert code in model_info["responses"]


def test_the_ml_operations_are_read_only_or_post_only(schema):
    assert set(schema["paths"]["/api/v1/ml/model"]) == {"get"}
    assert set(schema["paths"]["/api/v1/ml/no-show/predict"]) == {"post"}
from types import SimpleNamespace

from rest_framework.test import APIRequestFactory, force_authenticate

from predictions.views import SupervisedComparisonView

factory = APIRequestFactory()
URL = "/api/v1/ml/models/comparison"


def _user(role):
    return SimpleNamespace(is_authenticated=True, role=role, is_active=True)


def test_comparison_api_rejects_anonymous():
    req = factory.get(URL)
    res = SupervisedComparisonView.as_view()(req)
    assert res.status_code == 401


def test_comparison_api_rejects_admin():
    req = factory.get(URL)
    force_authenticate(req, user=_user("ADMIN"))
    res = SupervisedComparisonView.as_view()(req)
    assert res.status_code == 403


def test_comparison_api_accepts_member():
    req = factory.get(URL)
    force_authenticate(req, user=_user("USER"))
    res = SupervisedComparisonView.as_view()(req)
    assert res.status_code == 200
    data = res.data
    assert "comparison_table" in data
    assert "tuning" in data
    assert "dataset" in data
    assert len(data["comparison_table"]) >= 4


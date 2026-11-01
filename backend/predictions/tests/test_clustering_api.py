from types import SimpleNamespace

from rest_framework.test import APIRequestFactory, force_authenticate

from predictions.views import ClusteringAnalysisView

factory = APIRequestFactory()
URL = "/api/v1/ml/clusters"


def _user(role):
    return SimpleNamespace(is_authenticated=True, role=role, is_active=True)


def test_clustering_api_rejects_anonymous():
    req = factory.get(URL)
    res = ClusteringAnalysisView.as_view()(req)
    assert res.status_code == 401


def test_clustering_api_rejects_admin():
    req = factory.get(URL)
    force_authenticate(req, user=_user("ADMIN"))
    res = ClusteringAnalysisView.as_view()(req)
    assert res.status_code == 403


def test_clustering_api_accepts_member():
    req = factory.get(URL)
    force_authenticate(req, user=_user("USER"))
    res = ClusteringAnalysisView.as_view()(req)
    assert res.status_code == 200
    data = res.data
    assert "optimal_k" in data
    assert "k_evaluations" in data
    assert len(data["k_evaluations"]) >= 2
    assert "cluster_profiles" in data
    assert len(data["cluster_profiles"]) == data["optimal_k"]
    assert "methods_comparison" in data
    assert "pca_summary" in data
    assert "sample_points" in data
    assert "disclaimer" in data
    assert "EXPLORATORY OPERATIONAL ARCHETYPES" in data["disclaimer"]

from django.conf import settings
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from . import api_docs  # noqa: F401
from .health_views import HealthCheckView, ReadinessCheckView
from predictions.views import ClusteringAnalysisView, NoShowPredictView

urlpatterns = [
    # System Health & Readiness (Week 6 Capstone)
    path("health", HealthCheckView.as_view(), name="system-health"),
    path("health/", HealthCheckView.as_view()),
    path("ready", ReadinessCheckView.as_view(), name="system-ready"),
    path("ready/", ReadinessCheckView.as_view()),

    # Standard OpenAPI Versioned Endpoints (Week 6 Top-Level Aliases)
    path("api/v1/predict", NoShowPredictView.as_view(), name="api-v1-predict"),
    path("api/v1/predict/", NoShowPredictView.as_view()),
    path("api/v1/clusters", ClusteringAnalysisView.as_view(), name="api-v1-clusters"),
    path("api/v1/clusters/", ClusteringAnalysisView.as_view()),

    # Core Application Routes
    path("api/auth/", include("accounts.urls")),
    path("api/profiles/", include("profiles.urls")),
    path("api/admin/", include("accounts.admin_urls")),
    path("api/admin/", include("profiles.admin_urls")),
    path("api/admin/", include("audit.urls")),
    path("api/v1/ml/", include("predictions.urls")),
    path("api/v1/llm/", include("rag.urls")),
    path("api/v1/agents/", include("agents.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]

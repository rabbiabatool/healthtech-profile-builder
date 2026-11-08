from django.conf import settings
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from . import api_docs  # noqa: F401

urlpatterns = [
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

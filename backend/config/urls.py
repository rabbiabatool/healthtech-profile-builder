from django.urls import include, path

urlpatterns = [
    path("api/auth/", include("accounts.urls")),
    path("api/profiles/", include("profiles.urls")),
    path("api/admin/", include("accounts.admin_urls")),
    path("api/admin/", include("profiles.admin_urls")),
]
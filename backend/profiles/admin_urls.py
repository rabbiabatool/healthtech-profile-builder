from django.urls import path

from .admin_views import (
    AdminProfileDetailView,
    AdminProfileListView,
    DeactivateProfileView,
    ReactivateProfileView,
)

urlpatterns = [
    path("profiles", AdminProfileListView.as_view()),
    path("profiles/<int:pk>", AdminProfileDetailView.as_view()),
    path("profiles/<int:pk>/deactivate", DeactivateProfileView.as_view()),
    path("profiles/<int:pk>/reactivate", ReactivateProfileView.as_view()),
]
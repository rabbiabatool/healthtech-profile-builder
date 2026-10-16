from django.urls import path

from .admin_views import AdminProfileDetailView, AdminProfileListView, AdminProfileStatusView
from .models import ProfileStatus

urlpatterns = [
    path("profiles", AdminProfileListView.as_view()),
    path("profiles/<int:pk>", AdminProfileDetailView.as_view()),
    path(
        "profiles/<int:pk>/deactivate",
        AdminProfileStatusView.as_view(new_status=ProfileStatus.INACTIVE),
    ),
    path(
        "profiles/<int:pk>/reactivate",
        AdminProfileStatusView.as_view(new_status=ProfileStatus.ACTIVE),
    ),
]
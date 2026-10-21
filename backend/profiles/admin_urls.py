from django.urls import path

from audit.models import AuditAction

from .admin_views import AdminProfileDetailView, AdminProfileListView, AdminProfileStatusView
from .models import ProfileStatus

urlpatterns = [
    path("profiles", AdminProfileListView.as_view()),
    path("profiles/<int:pk>", AdminProfileDetailView.as_view()),
    path(
        "profiles/<int:pk>/deactivate",
        AdminProfileStatusView.as_view(
            new_status=ProfileStatus.INACTIVE,
            audit_action=AuditAction.ADMIN_PROFILE_DEACTIVATED,
        ),
    ),
    path(
        "profiles/<int:pk>/reactivate",
        AdminProfileStatusView.as_view(
            new_status=ProfileStatus.ACTIVE,
            audit_action=AuditAction.ADMIN_PROFILE_REACTIVATED,
        ),
    ),
]
from django.urls import path

from .views import AuditEventListView, ProfileAuditTimelineView

urlpatterns = [
    path("audit-events", AuditEventListView.as_view()),
    path("profiles/<int:profile_id>/audit-events", ProfileAuditTimelineView.as_view()),
]

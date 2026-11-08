"""URL routes for Controlled AI Agents (Week 5)."""
from django.urls import path
from agents.views import AgentChatView, SchemaValidationUtilityView, SessionDetailView

urlpatterns = [
    path("chat/", AgentChatView.as_view(), name="agent-chat"),
    path("sessions/<str:session_id>/", SessionDetailView.as_view(), name="agent-session-detail"),
    path("validate-schema/", SchemaValidationUtilityView.as_view(), name="agent-validate-schema"),
]

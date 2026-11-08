"""URL routes for Controlled AI Agents (Week 5)."""
from django.urls import path
from agents.views import (
    AgentChatView,
    AgentWorkflowView,
    MCPToolCallView,
    SchemaValidationUtilityView,
    SessionDetailView,
    ToolsListView,
)

urlpatterns = [
    path("chat/", AgentChatView.as_view(), name="agent-chat"),
    path("workflow/", AgentWorkflowView.as_view(), name="agent-workflow"),
    path("tools/", ToolsListView.as_view(), name="agent-tools-list"),
    path("mcp/call/", MCPToolCallView.as_view(), name="agent-mcp-call"),
    path("sessions/<str:session_id>/", SessionDetailView.as_view(), name="agent-session-detail"),
    path("validate-schema/", SchemaValidationUtilityView.as_view(), name="agent-validate-schema"),
]

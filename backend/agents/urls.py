"""URL routes for Controlled AI Agents, Multi-Step Planner, Task Queue & Admin Audit (Week 5)."""
from django.urls import path
from agents.admin_views import (
    AdminAuditDashboardView,
    ModelMonitoringMetricsView,
    TaskJobDetailView,
    TaskJobListView,
    TaskJobSubmitView,
)
from agents.views import (
    AgentChatView,
    AgentWorkflowView,
    MCPToolCallView,
    SchemaValidationUtilityView,
    SessionDetailView,
    ToolsListView,
)

urlpatterns = [
    # Multi-turn chat & validation
    path("chat/", AgentChatView.as_view(), name="agent-chat"),
    path("chat", AgentChatView.as_view()),
    path("workflow/", AgentWorkflowView.as_view(), name="agent-workflow"),
    path("workflow", AgentWorkflowView.as_view()),
    path("tools/", ToolsListView.as_view(), name="agent-tools-list"),
    path("tools", ToolsListView.as_view()),
    path("mcp/call/", MCPToolCallView.as_view(), name="agent-mcp-call"),
    path("mcp/call", MCPToolCallView.as_view()),
    path("sessions/<str:session_id>/", SessionDetailView.as_view(), name="agent-session-detail"),
    path("sessions/<str:session_id>", SessionDetailView.as_view()),
    path("validate-schema/", SchemaValidationUtilityView.as_view(), name="agent-validate-schema"),
    path("validate-schema", SchemaValidationUtilityView.as_view()),

    # Background task queue
    path("jobs/", TaskJobSubmitView.as_view(), name="agent-jobs-submit"),
    path("jobs", TaskJobSubmitView.as_view()),
    path("jobs/list/", TaskJobListView.as_view(), name="agent-jobs-list"),
    path("jobs/list", TaskJobListView.as_view()),
    path("jobs/<str:job_id>/", TaskJobDetailView.as_view(), name="agent-job-detail"),
    path("jobs/<str:job_id>", TaskJobDetailView.as_view()),

    # Model monitoring & drift telemetry
    path("monitoring/metrics/", ModelMonitoringMetricsView.as_view(), name="agent-monitoring-metrics"),
    path("monitoring/metrics", ModelMonitoringMetricsView.as_view()),

    # Admin audit dashboard
    path("admin/audit/", AdminAuditDashboardView.as_view(), name="agent-admin-audit"),
    path("admin/audit", AdminAuditDashboardView.as_view()),
]

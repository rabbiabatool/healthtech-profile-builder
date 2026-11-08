"""Tests for Week 5 Phase 3: Controlled Tool-Using Agent, 5 Typed Tools, MCP Adapter & Multi-Step Planner."""
import uuid
from types import SimpleNamespace
import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from agents.mcp_adapter import get_mcp_adapter
from agents.planner import MultiStepAgentPlanner
from agents.tools import (
    CheckAppointmentAvailabilityTool,
    RequestSupervisedPredictionTool,
    RetrieveClusterSummariesTool,
    ScheduleMockAppointmentTool,
    SearchApprovedDocumentsTool,
)
from agents.views import (
    AgentWorkflowView,
    MCPToolCallView,
    ToolsListView,
)


@pytest.fixture
def auth_user():
    return SimpleNamespace(is_authenticated=True, is_active=True, role="USER", email="user@clinic.test", id=1)


@pytest.fixture
def admin_user():
    return SimpleNamespace(is_authenticated=True, is_active=True, role="ADMIN", email="admin@clinic.test", id=2)


@pytest.fixture
def unauth_user():
    return SimpleNamespace(is_authenticated=False, is_active=False, role="ANON", email="anon@test", id=None)


# ─── Unit Tests: 5 Typed Tools ───────────────────────────────────────────────

def test_tool_1_search_approved_documents(auth_user):
    tool = SearchApprovedDocumentsTool()
    res = tool.execute(user=auth_user, arguments={"query": "cancellation policy for specialists"})
    assert res.status == "success"
    assert res.result_data["count"] > 0
    assert any("cancellation" in p["doc_name"].lower() for p in res.result_data["passages"])


def test_tool_2_check_appointment_availability(auth_user):
    tool = CheckAppointmentAvailabilityTool()
    # Success case
    res = tool.execute(user=auth_user, arguments={"department": "cardiology", "date": "2026-11-20"})
    assert res.status == "success"
    assert "11:00" in res.result_data["available_slots"]

    # Graceful failure case on unknown department
    res_fail = tool.execute(user=auth_user, arguments={"department": "neuro_surgery", "date": "2026-11-20"})
    assert res_fail.status == "failed"
    assert "Unknown department" in res_fail.error


def test_tool_3_request_supervised_prediction(auth_user):
    tool = RequestSupervisedPredictionTool()
    res = tool.execute(
        user=auth_user,
        arguments={"patient_features": {"age": 50, "lead_time_days": 30, "previous_no_shows": 2}},
    )
    assert res.status == "success"
    assert 0.0 <= res.result_data["no_show_probability"] <= 1.0
    assert res.result_data["risk_band"] in ["LOW", "MEDIUM", "HIGH"]
    assert "no clinical diagnostic" in res.result_data["disclaimer"].lower()


def test_tool_4_retrieve_cluster_summaries(auth_user):
    tool = RetrieveClusterSummariesTool()
    # All personas
    res_all = tool.execute(user=auth_user, arguments={})
    assert res_all.status == "success"
    assert len(res_all.result_data["personas"]) == 6

    # Specific persona
    res_single = tool.execute(user=auth_user, arguments={"cluster_id": 0})
    assert res_single.status == "success"
    assert res_single.result_data["personas"]["name"] == "Digital Proactives"


def test_tool_5_schedule_mock_appointment_write_protection(auth_user):
    tool = ScheduleMockAppointmentTool()
    idem_key = str(uuid.uuid4())

    # 1. Unconfirmed write: MUST be blocked with confirmation_required
    res_unconfirmed = tool.execute(
        user=auth_user,
        arguments={
            "department": "general_practice",
            "date": "2026-11-25",
            "slot_time": "14:00",
            "reason": "Annual checkup",
            "human_confirmation": False,
            "idempotency_key": idem_key,
        },
    )
    assert res_unconfirmed.status == "confirmation_required"
    assert "Explicit human confirmation is required" in res_unconfirmed.error
    assert res_unconfirmed.result_data["draft"]["status"] == "DRAFT_PENDING_CONFIRMATION"

    # 2. Confirmed write: MUST succeed and return booking ID
    res_confirmed = tool.execute(
        user=auth_user,
        arguments={
            "department": "general_practice",
            "date": "2026-11-25",
            "slot_time": "14:00",
            "reason": "Annual checkup",
            "human_confirmation": True,
            "idempotency_key": idem_key,
        },
    )
    assert res_confirmed.status == "success"
    booking_id = res_confirmed.result_data["booking_id"]
    assert booking_id.startswith("APPT-")

    # 3. Idempotency Replay: Submitting identical key returns existing record without double write
    res_replay = tool.execute(
        user=auth_user,
        arguments={
            "department": "general_practice",
            "date": "2026-11-25",
            "slot_time": "14:00",
            "reason": "Annual checkup",
            "human_confirmation": True,
            "idempotency_key": idem_key,
        },
    )
    assert res_replay.status == "success"
    assert res_replay.result_data["idempotency_replay"] is True
    assert res_replay.result_data["appointment"]["booking_id"] == booking_id


def test_tool_authorization_denial(unauth_user):
    tool = CheckAppointmentAvailabilityTool()
    res = tool.execute(user=unauth_user, arguments={"department": "cardiology"})
    assert res.status == "denied"
    assert "Access denied" in res.error


# ─── Unit Tests: MCP Tool Adapter ────────────────────────────────────────────

def test_mcp_adapter_list_tools():
    adapter = get_mcp_adapter()
    tools = adapter.list_mcp_tools()
    assert len(tools) == 5
    for t in tools:
        assert "name" in t
        assert "description" in t
        assert "inputSchema" in t
        assert t["inputSchema"]["type"] == "object"


def test_mcp_adapter_call_tool_and_redaction(auth_user):
    adapter = get_mcp_adapter()
    # Call with PII in query
    res = adapter.call_mcp_tool(
        tool_name="search_approved_documents",
        arguments={"query": "patient with SSN 123-45-6789 asks about cancellation"},
        user=auth_user,
    )
    assert res["isError"] is False
    content_text = res["content"][0]["text"]
    assert "[REDACTED_SSN]" in content_text
    assert "123-45-6789" not in content_text


def test_mcp_adapter_denied_permission(unauth_user):
    adapter = get_mcp_adapter()
    res = adapter.call_mcp_tool(
        tool_name="check_appointment_availability",
        arguments={"department": "cardiology"},
        user=unauth_user,
    )
    assert res["isError"] is True
    assert "Permission Denied" in res["content"][0]["text"]


# ─── Unit Tests: Multi-Step Stateful Planner ─────────────────────────────────

def test_multistep_workflow_scheduling_flow(auth_user):
    planner = MultiStepAgentPlanner(max_steps=5)
    
    # 1. First run without confirmation: should stop at write gate with confirmation prompt
    state = planner.execute_workflow(
        user_query="I want to book an appointment with cardiology next week",
        user=auth_user,
        human_confirmed=False,
    )
    assert state.requires_human_confirmation is True
    assert state.pending_draft is not None
    assert state.pending_draft["department"] == "cardiology"
    assert len(state.traces) >= 3
    assert state.traces[0].phase == "plan"

    # 2. Second run with explicit human confirmation: should complete booking
    confirmed_state = planner.execute_workflow(
        user_query="I want to book an appointment with cardiology next week",
        user=auth_user,
        human_confirmed=True,
        idempotency_key=state.pending_draft["idempotency_key"],
    )
    assert confirmed_state.is_completed is True
    assert confirmed_state.requires_human_confirmation is False
    assert confirmed_state.final_response["status"] == "completed"
    assert "Booking confirmed" in confirmed_state.final_response["answer"]


def test_multistep_workflow_dynamic_datetime_extraction(auth_user):
    planner = MultiStepAgentPlanner(max_steps=5)
    query = "I want to book an appointment with cardiology next week on Tuesday 11:00 am"
    state = planner.execute_workflow(
        user_query=query,
        user=auth_user,
        human_confirmed=False,
    )
    assert state.requires_human_confirmation is True
    assert state.pending_draft is not None
    assert state.pending_draft["department"] == "cardiology"
    assert state.pending_draft["date"] == "2026-11-17"  # Next Tuesday
    assert state.pending_draft["slot_time"] == "11:00"  # Exact requested & available slot
    assert "11:00" in state.confirmation_prompt

    # When confirmed
    confirmed = planner.execute_workflow(
        user_query=query,
        user=auth_user,
        human_confirmed=True,
        idempotency_key=state.pending_draft["idempotency_key"],
    )
    assert confirmed.is_completed is True
    assert "2026-11-17 at 11:00" in confirmed.final_response["answer"]


def test_multistep_workflow_ml_persona_flow(auth_user):
    planner = MultiStepAgentPlanner(max_steps=5)
    state = planner.execute_workflow(
        user_query="Evaluate attendance risk and persona for this patient",
        user=auth_user,
    )
    assert state.is_completed is True
    assert len(state.traces) >= 3
    assert "No-show risk" in state.final_response["answer"]
    assert "personas retrieved" in state.final_response["answer"]


def test_multistep_workflow_unauthorized_tool_denial(unauth_user):
    planner = MultiStepAgentPlanner(max_steps=5)
    state = planner.execute_workflow(
        user_query="Check cardiology appointments",
        user=unauth_user,
    )
    assert state.final_response["status"] == "denied"
    assert any(t.status == "denied" for t in state.traces)


def test_multistep_workflow_max_steps_limit(auth_user):
    # Create planner with low step bound of 2
    bounded_planner = MultiStepAgentPlanner(max_steps=2)
    state = bounded_planner.execute_workflow(
        user_query="I want to book an appointment with cardiology next week",
        user=auth_user,
        human_confirmed=True,
    )
    # Must exit gracefully when hitting max steps limit
    assert any("exceeded maximum step limit" in t.details for t in state.traces)
    assert len(state.traces) <= 5


# ─── Integration Tests: Agent Workflow REST APIs ──────────────────────────────

@pytest.fixture
def api_client():
    return APIRequestFactory()


def test_api_workflow_endpoint(api_client, auth_user):
    view = AgentWorkflowView.as_view()
    req = api_client.post(
        "/api/v1/agents/workflow/",
        data={"query": "Evaluate attendance risk and cluster persona for patient"},
        format="json",
    )
    force_authenticate(req, user=auth_user)
    resp = view(req)
    assert resp.status_code == 200
    data = resp.data
    assert "workflow_id" in data
    assert len(data["traces"]) >= 3
    assert data["is_completed"] is True


def test_api_tools_list_endpoint(api_client, auth_user):
    view = ToolsListView.as_view()
    req = api_client.get("/api/v1/agents/tools/")
    force_authenticate(req, user=auth_user)
    resp = view(req)
    assert resp.status_code == 200
    assert len(resp.data["tools"]) == 5


def test_api_mcp_call_endpoint(api_client, auth_user):
    view = MCPToolCallView.as_view()
    req = api_client.post(
        "/api/v1/agents/mcp/call/",
        data={
            "name": "check_appointment_availability",
            "arguments": {"department": "telehealth", "date": "2026-11-20"},
        },
        format="json",
    )
    force_authenticate(req, user=auth_user)
    resp = view(req)
    assert resp.status_code == 200
    assert resp.data["isError"] is False
    assert "08:30" in resp.data["content"][0]["text"]

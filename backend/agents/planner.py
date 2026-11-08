"""Multi-Step Stateful Agent Planner & Execution Engine (Week 5 Phase 3).

Implements the complete stateful multi-step workflow:
Plan -> Tool Selection -> Validation -> Execution -> Recovery -> Final Response.
Features:
- Step-by-step execution traces with latency and sanitized arguments.
- Strict maximum-step bound (max 5 steps) preventing infinite loops.
- Server-side runtime authorization check per tool.
- Human-in-the-loop write gate with draft confirmation tokens.
- Graceful recovery and fallback upon failed tool invocations.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from agents.redaction import check_prompt_security, redact_sensitive_data, sanitize_dict_deep
from agents.schemas import CitationItem, StructuredAgentResponse, ToolCallRequest, ToolExecutionResult
from agents.tools import TOOL_REGISTRY, BaseAgentTool, get_tool


@dataclass
class WorkflowStepTrace:
    step_number: int
    phase: str  # "plan", "tool_selection", "validation", "execution", "recovery", "response"
    tool_name: Optional[str] = None
    sanitized_arguments: Dict[str, Any] = field(default_factory=dict)
    status: str = "success"  # "success", "denied", "failed", "confirmation_required", "recovered"
    details: str = ""
    latency_ms: float = 0.0


@dataclass
class MultiStepWorkflowState:
    workflow_id: str
    user_query: str
    session_id: str
    current_step: int = 0
    max_steps: int = 5
    traces: List[WorkflowStepTrace] = field(default_factory=list)
    is_completed: bool = False
    requires_human_confirmation: bool = False
    confirmation_prompt: Optional[str] = None
    pending_draft: Optional[Dict[str, Any]] = None
    final_response: Optional[Dict[str, Any]] = None


class MultiStepAgentPlanner:
    """Stateful agent orchestrating multi-tool administrative healthcare workflows."""

    def __init__(self, max_steps: int = 5):
        self.max_steps = max_steps

    def execute_workflow(
        self,
        user_query: str,
        user: Any,
        session_id: str = "default_session",
        human_confirmed: bool = False,
        idempotency_key: Optional[str] = None,
        force_tool_sequence: Optional[List[Dict[str, Any]]] = None,
    ) -> MultiStepWorkflowState:
        workflow_id = f"wf-{int(time.time())}-{str(uuid.uuid4())[:6]}"
        sanitized_query, _ = redact_sensitive_data(user_query)

        state = MultiStepWorkflowState(
            workflow_id=workflow_id,
            user_query=sanitized_query,
            session_id=session_id,
            max_steps=self.max_steps,
        )

        # Step 0: Security & Safety Guard
        sec = check_prompt_security(sanitized_query)
        if not sec["is_safe"]:
            state.traces.append(WorkflowStepTrace(
                step_number=1,
                phase="plan",
                status="failed",
                details=f"Security violation detected: {sec['reason']}. Workflow aborted.",
            ))
            state.is_completed = True
            state.final_response = {
                "intent": "refusal",
                "status": "refused",
                "answer": f"Request refused: {sec['reason']}",
                "safety_flag": True,
                "safety_reason": sec["reason"],
            }
            return state

        # Determine Planned Tool Sequence
        planned_tools: List[Dict[str, Any]] = []
        if force_tool_sequence:
            planned_tools = force_tool_sequence
        else:
            q_lower = sanitized_query.lower()
            # Scenario A: Scheduling workflow (Check policy -> check availability -> draft/schedule appointment)
            if any(k in q_lower for k in ["book", "schedule", "appointment", "reserve"]):
                dept = "general_practice"
                if "cardio" in q_lower:
                    dept = "cardiology"
                elif "telehealth" in q_lower or "video" in q_lower:
                    dept = "telehealth"
                elif "pediatric" in q_lower or "child" in q_lower:
                    dept = "pediatrics"

                planned_tools.append({
                    "tool": "search_approved_documents",
                    "args": {"query": f"{dept} appointment booking cancellation policy", "top_k": 2},
                })
                planned_tools.append({
                    "tool": "check_appointment_availability",
                    "args": {"department": dept, "date": "2026-11-20"},
                })
                planned_tools.append({
                    "tool": "schedule_mock_appointment",
                    "args": {
                        "department": dept,
                        "date": "2026-11-20",
                        "slot_time": "10:30",
                        "reason": "Consultation",
                        "human_confirmation": human_confirmed,
                        "idempotency_key": idempotency_key or f"idem-{workflow_id}",
                    },
                })

            # Scenario B: ML Risk & Persona Analysis
            elif any(k in q_lower for k in ["risk", "no-show", "prediction", "cluster", "persona"]):
                planned_tools.append({
                    "tool": "request_supervised_prediction",
                    "args": {
                        "patient_features": {
                            "age": 45,
                            "lead_time_days": 21,
                            "previous_no_shows": 1,
                        }
                    },
                })
                planned_tools.append({
                    "tool": "retrieve_cluster_summaries",
                    "args": {"cluster_id": 1},
                })

            # Scenario C: Policy Documentation Search
            else:
                planned_tools.append({
                    "tool": "search_approved_documents",
                    "args": {"query": sanitized_query, "top_k": 3},
                })

        # Phase 1: Record High-Level Plan
        state.traces.append(WorkflowStepTrace(
            step_number=1,
            phase="plan",
            details=f"Planned {len(planned_tools)} sequential tools: {[t['tool'] for t in planned_tools]}",
        ))

        step_counter = 2
        tool_results_summary = []

        # Execute Multi-Step Loop (bounded by max_steps)
        for tool_spec in planned_tools:
            if step_counter > self.max_steps:
                state.traces.append(WorkflowStepTrace(
                    step_number=step_counter,
                    phase="recovery",
                    status="failed",
                    details=f"Workflow exceeded maximum step limit ({self.max_steps}). Forcing graceful exit.",
                ))
                break

            tool_name = tool_spec["tool"]
            tool_args = sanitize_dict_deep(tool_spec.get("args", {}))
            tool_instance = get_tool(tool_name)

            # Tool Selection & Validation Phase
            if not tool_instance:
                state.traces.append(WorkflowStepTrace(
                    step_number=step_counter,
                    phase="tool_selection",
                    tool_name=tool_name,
                    status="failed",
                    details=f"Tool '{tool_name}' not found in registry.",
                ))
                step_counter += 1
                continue

            # Server-side Authorization Check Phase
            auth_ok = tool_instance.authorize(user)
            if not auth_ok:
                state.traces.append(WorkflowStepTrace(
                    step_number=step_counter,
                    phase="validation",
                    tool_name=tool_name,
                    sanitized_arguments=tool_args,
                    status="denied",
                    details=f"Authorization failure: User lacks required role '{tool_instance.required_role}'.",
                ))
                state.is_completed = True
                state.final_response = {
                    "intent": "refusal",
                    "status": "denied",
                    "answer": f"Tool execution denied: User role is not authorized for '{tool_name}'.",
                }
                return state

            # Execution Phase
            t_start = time.time()
            exec_res = tool_instance.execute(
                user=user,
                arguments=tool_args,
                human_confirmed=human_confirmed,
                idempotency_key=idempotency_key or tool_args.get("idempotency_key"),
            )
            exec_latency = round((time.time() - t_start) * 1000, 2)

            state.traces.append(WorkflowStepTrace(
                step_number=step_counter,
                phase="execution",
                tool_name=tool_name,
                sanitized_arguments=tool_args,
                status=exec_res.status,
                details=f"Executed with status '{exec_res.status}'.",
                latency_ms=exec_latency,
            ))
            step_counter += 1

            # Handle Human Confirmation Gate (Write Tool)
            if exec_res.status == "confirmation_required":
                state.requires_human_confirmation = True
                state.confirmation_prompt = exec_res.result_data.get("prompt_message")
                state.pending_draft = exec_res.result_data.get("draft")
                state.is_completed = False
                state.final_response = {
                    "intent": "appointment_booking",
                    "status": "needs_confirmation",
                    "answer": exec_res.result_data.get("prompt_message"),
                    "pending_draft": state.pending_draft,
                }
                return state

            # Handle Tool Failure & Recovery
            if exec_res.status == "failed":
                state.traces.append(WorkflowStepTrace(
                    step_number=step_counter,
                    phase="recovery",
                    tool_name=tool_name,
                    status="recovered",
                    details=f"Recovered from failed tool '{tool_name}': {exec_res.error}. Continuing workflow.",
                ))
                step_counter += 1

            tool_results_summary.append({
                "tool": tool_name,
                "status": exec_res.status,
                "data": exec_res.result_data,
            })

        # Phase 5: Synthesis / Response Phase
        state.is_completed = True
        state.traces.append(WorkflowStepTrace(
            step_number=step_counter,
            phase="response",
            details="Successfully synthesized final workflow response from all execution traces.",
        ))

        # Build synthesized answer
        answer_parts = []
        for item in tool_results_summary:
            t = item["tool"]
            d = item["data"]
            if t == "search_approved_documents":
                count = d.get("count", 0)
                answer_parts.append(f"Retrieved {count} policy passages.")
            elif t == "check_appointment_availability":
                slots = ", ".join(d.get("available_slots", []))
                answer_parts.append(f"Available slots for {d.get('department')}: {slots}.")
            elif t == "schedule_mock_appointment":
                answer_parts.append(f"Booking confirmed: {d.get('message')}")
            elif t == "request_supervised_prediction":
                answer_parts.append(f"No-show risk: {d.get('risk_band')} ({d.get('no_show_probability') * 100:.1f}%). {d.get('recommended_intervention')}")
            elif t == "retrieve_cluster_summaries":
                answer_parts.append("Aggregated patient personas retrieved.")

        final_answer = " ".join(answer_parts) if answer_parts else "Multi-step workflow completed."
        state.final_response = {
            "workflow_id": workflow_id,
            "intent": "multi_tool_workflow",
            "status": "completed",
            "answer": final_answer,
            "tool_count": len(tool_results_summary),
            "step_count": step_counter,
        }

        return state


"""Five Typed Tools for Controlled Healthcare Assistant Agents (Week 5 Phase 3).

Includes read-only analytical tools and human-in-the-loop write tools with
server-side permission enforcement, idempotency keys, and PII redaction.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from agents.redaction import redact_sensitive_data, sanitize_dict_deep
from agents.schemas import ToolExecutionResult
from rag.advanced_engine import get_advanced_store


# In-memory mock appointment registry for write tool idempotency
_MOCK_APPOINTMENTS_STORE: Dict[str, Dict[str, Any]] = {}
_IDEMPOTENCY_STORE: Dict[str, Dict[str, Any]] = {}


class BaseAgentTool:
    """Base class for all typed agent tools."""
    name: str = ""
    description: str = ""
    is_write_tool: bool = False
    required_role: str = "USER"  # "USER", "ADMIN", or "ANY"

    def authorize(self, user: Any) -> bool:
        """Enforces server-side authorization at execution time."""
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if not getattr(user, "is_active", True):
            return False
        if self.required_role == "ANY":
            return True
        user_role = getattr(user, "role", "USER")
        if self.required_role == "ADMIN" and user_role != "ADMIN":
            return False
        return True

    def execute(
        self,
        user: Any,
        arguments: Dict[str, Any],
        human_confirmed: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> ToolExecutionResult:
        raise NotImplementedError


# ─── Tool 1: Search Approved Documents ───────────────────────────────────────

class SearchApprovedDocumentsTool(BaseAgentTool):
    name = "search_approved_documents"
    description = "Searches approved clinic policies, scheduling rules, and patient rights documentation."
    is_write_tool = False
    required_role = "ANY"

    def execute(
        self,
        user: Any,
        arguments: Dict[str, Any],
        human_confirmed: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> ToolExecutionResult:
        t0 = time.time()
        if not self.authorize(user):
            return ToolExecutionResult(
                tool_name=self.name,
                status="denied",
                error="Access denied: authentication required to search clinic documents.",
                execution_latency_ms=round((time.time() - t0) * 1000, 2),
            )

        query = str(arguments.get("query", "")).strip()
        if not query:
            return ToolExecutionResult(
                tool_name=self.name,
                status="failed",
                error="Query parameter cannot be empty.",
                execution_latency_ms=round((time.time() - t0) * 1000, 2),
            )

        category = arguments.get("category")
        filter_meta = {"category": category} if category else None
        top_k = min(5, max(1, int(arguments.get("top_k", 3))))

        store = get_advanced_store()
        passages = store.retrieve_hybrid(query, top_k=top_k, filter_metadata=filter_meta)

        results = [
            {
                "doc_name": p["doc_name"],
                "version": p["version"],
                "text": p["text"],
                "score": round(p["score"], 4),
            }
            for p in passages
        ]

        return ToolExecutionResult(
            tool_name=self.name,
            status="success",
            result_data={"query": query, "passages": results, "count": len(results)},
            execution_latency_ms=round((time.time() - t0) * 1000, 2),
        )


# ─── Tool 2: Check Fictional Appointment Availability ────────────────────────

class CheckAppointmentAvailabilityTool(BaseAgentTool):
    name = "check_appointment_availability"
    description = "Checks fictional appointment slot availability for clinic departments."
    is_write_tool = False
    required_role = "USER"

    AVAILABLE_SLOTS_TABLE = {
        "general_practice": ["09:00", "10:30", "13:00", "15:30"],
        "cardiology": ["11:00", "14:00"],
        "telehealth": ["08:30", "10:00", "11:30", "14:30", "16:00"],
        "pediatrics": ["09:30", "11:00", "13:30"],
    }

    def execute(
        self,
        user: Any,
        arguments: Dict[str, Any],
        human_confirmed: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> ToolExecutionResult:
        t0 = time.time()
        if not self.authorize(user):
            return ToolExecutionResult(
                tool_name=self.name,
                status="denied",
                error="Access denied: Standard User role required to check availability.",
                execution_latency_ms=round((time.time() - t0) * 1000, 2),
            )

        department = str(arguments.get("department", "general_practice")).lower().replace(" ", "_")
        date_str = str(arguments.get("date", "2026-11-15"))

        slots = self.AVAILABLE_SLOTS_TABLE.get(department)
        if slots is None:
            return ToolExecutionResult(
                tool_name=self.name,
                status="failed",
                error=f"Unknown department '{department}'. Supported: {list(self.AVAILABLE_SLOTS_TABLE.keys())}",
                execution_latency_ms=round((time.time() - t0) * 1000, 2),
            )

        return ToolExecutionResult(
            tool_name=self.name,
            status="success",
            result_data={
                "department": department,
                "date": date_str,
                "available_slots": slots,
                "is_available": len(slots) > 0,
            },
            execution_latency_ms=round((time.time() - t0) * 1000, 2),
        )


# ─── Tool 3: Request Supervised ML Prediction ────────────────────────────────

class RequestSupervisedPredictionTool(BaseAgentTool):
    name = "request_supervised_prediction"
    description = "Invokes the supervised ML model to compute synthetic appointment attendance risk."
    is_write_tool = False
    required_role = "USER"

    def execute(
        self,
        user: Any,
        arguments: Dict[str, Any],
        human_confirmed: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> ToolExecutionResult:
        t0 = time.time()
        if not self.authorize(user):
            return ToolExecutionResult(
                tool_name=self.name,
                status="denied",
                error="Access denied: Standard User role required to request ML inference.",
                execution_latency_ms=round((time.time() - t0) * 1000, 2),
            )

        features = arguments.get("patient_features", {})
        age = float(features.get("age", 40))
        lead_time = float(features.get("lead_time_days", 14))
        prior_no_shows = int(features.get("previous_no_shows", 0))

        # Synthetic logistic scoring aligned with Week 3/4 baseline
        logit = -1.8 + (lead_time * 0.04) + (prior_no_shows * 0.8) - (age * 0.01)
        prob = 1.0 / (1.0 + (2.71828 ** (-logit)))
        prob = max(0.01, min(0.99, round(prob, 3)))

        if prob >= 0.40:
            band = "HIGH"
            action = "Send automated 48h and 2h SMS reminder + offer telehealth conversion option."
        elif prob >= 0.20:
            band = "MEDIUM"
            action = "Standard 24h reminder via patient portal."
        else:
            band = "LOW"
            action = "Standard routine confirmation notice."

        return ToolExecutionResult(
            tool_name=self.name,
            status="success",
            result_data={
                "no_show_probability": prob,
                "risk_band": band,
                "recommended_intervention": action,
                "model_version": "v1.0.0-supervised",
                "disclaimer": "Operational heuristic only; no clinical diagnostic impact.",
            },
            execution_latency_ms=round((time.time() - t0) * 1000, 2),
        )


# ─── Tool 4: Retrieve Anonymized Cluster Summaries ───────────────────────────

class RetrieveClusterSummariesTool(BaseAgentTool):
    name = "retrieve_cluster_summaries"
    description = "Retrieves non-sensitive, aggregated patient engagement cluster personas."
    is_write_tool = False
    required_role = "USER"

    CLUSTER_PERSONAS = [
        {"cluster_id": 0, "name": "Digital Proactives", "share_pct": 28.5, "avg_lead_time": 6.2, "attendance_rate": 96.2, "note": "High portal engagement and fast response."},
        {"cluster_id": 1, "name": "Long-Horizon Planners", "share_pct": 21.3, "avg_lead_time": 45.1, "attendance_rate": 84.0, "note": "Book weeks in advance; benefit from dual SMS reminders."},
        {"cluster_id": 2, "name": "Same-Day Urgent Needs", "share_pct": 18.2, "avg_lead_time": 1.1, "attendance_rate": 91.5, "note": "Short notice appointments with strong completion rates."},
        {"cluster_id": 3, "name": "At-Risk Reschedulers", "share_pct": 14.0, "avg_lead_time": 22.4, "attendance_rate": 62.8, "note": "Frequent cancellations; benefit from flexible telehealth slots."},
        {"cluster_id": 4, "name": "Weekend & Evening Seekers", "share_pct": 11.0, "avg_lead_time": 12.0, "attendance_rate": 89.1, "note": "Strong preference for extended operational hours."},
        {"cluster_id": 5, "name": "Specialist Consult Patients", "share_pct": 7.0, "avg_lead_time": 30.5, "attendance_rate": 88.4, "note": "Requires 48h cancellation notice for imaging and specialist care."},
    ]

    def execute(
        self,
        user: Any,
        arguments: Dict[str, Any],
        human_confirmed: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> ToolExecutionResult:
        t0 = time.time()
        if not self.authorize(user):
            return ToolExecutionResult(
                tool_name=self.name,
                status="denied",
                error="Access denied: Standard User role required to view cluster personas.",
                execution_latency_ms=round((time.time() - t0) * 1000, 2),
            )

        cid = arguments.get("cluster_id")
        if cid is not None:
            matched = [c for c in self.CLUSTER_PERSONAS if c["cluster_id"] == int(cid)]
            data = matched[0] if matched else None
            if not data:
                return ToolExecutionResult(
                    tool_name=self.name,
                    status="failed",
                    error=f"Cluster id {cid} not found (0-5).",
                    execution_latency_ms=round((time.time() - t0) * 1000, 2),
                )
        else:
            data = self.CLUSTER_PERSONAS

        return ToolExecutionResult(
            tool_name=self.name,
            status="success",
            result_data={"personas": data, "algorithm": "K-Means (k=6) + Agglomerative (Ward)"},
            execution_latency_ms=round((time.time() - t0) * 1000, 2),
        )


# ─── Tool 5: Schedule Mock Appointment (WRITE TOOL) ──────────────────────────

class ScheduleMockAppointmentTool(BaseAgentTool):
    name = "schedule_mock_appointment"
    description = (
        "Drafts or commits a fictional appointment booking or reminder. "
        "CRITICAL: Requires explicit human confirmation flag and unique idempotency key."
    )
    is_write_tool = True
    required_role = "USER"

    def execute(
        self,
        user: Any,
        arguments: Dict[str, Any],
        human_confirmed: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> ToolExecutionResult:
        t0 = time.time()
        # 1. Server-side authorization check
        if not self.authorize(user):
            return ToolExecutionResult(
                tool_name=self.name,
                status="denied",
                error="Access denied: write operation requires authenticated User or Admin session.",
                execution_latency_ms=round((time.time() - t0) * 1000, 2),
            )

        # 2. Extract and sanitize inputs
        department = str(arguments.get("department", "general_practice")).strip()
        date_str = str(arguments.get("date", "2026-11-15")).strip()
        slot_time = str(arguments.get("slot_time", "10:00")).strip()
        reason = str(arguments.get("reason", "Routine checkup")).strip()
        sanitized_reason, _ = redact_sensitive_data(reason)

        idem_key = idempotency_key or arguments.get("idempotency_key")
        if not idem_key:
            idem_key = str(uuid.uuid4())

        # 3. Check Idempotency Key
        if idem_key in _IDEMPOTENCY_STORE:
            prior_record = _IDEMPOTENCY_STORE[idem_key]
            return ToolExecutionResult(
                tool_name=self.name,
                status="success",
                result_data={
                    "appointment": prior_record,
                    "idempotency_replay": True,
                    "message": "Returned existing booking matching idempotency key.",
                },
                execution_latency_ms=round((time.time() - t0) * 1000, 2),
            )

        # 4. Human-in-the-Loop Confirmation Gate
        explicit_confirmation = human_confirmed or bool(arguments.get("human_confirmation", False))
        if not explicit_confirmation:
            draft_summary = {
                "department": department,
                "date": date_str,
                "slot_time": slot_time,
                "reason": sanitized_reason,
                "idempotency_key": idem_key,
                "status": "DRAFT_PENDING_CONFIRMATION",
            }
            return ToolExecutionResult(
                tool_name=self.name,
                status="confirmation_required",
                result_data={
                    "draft": draft_summary,
                    "prompt_message": (
                        f"Please confirm: Do you wish to book a fictional {department} appointment "
                        f"on {date_str} at {slot_time} for '{sanitized_reason}'? (Idempotency key: {idem_key})"
                    ),
                },
                error="Explicit human confirmation is required before committing writes.",
                execution_latency_ms=round((time.time() - t0) * 1000, 2),
            )

        # 5. Commit Authorized Write
        booking_id = f"APPT-{int(time.time())}-{str(uuid.uuid4())[:6]}"
        record = {
            "booking_id": booking_id,
            "department": department,
            "date": date_str,
            "slot_time": slot_time,
            "reason": sanitized_reason,
            "confirmed_by_user": getattr(user, "email", "user@clinic.test"),
            "idempotency_key": idem_key,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        _MOCK_APPOINTMENTS_STORE[booking_id] = record
        _IDEMPOTENCY_STORE[idem_key] = record

        return ToolExecutionResult(
            tool_name=self.name,
            status="success",
            result_data={
                "booking_id": booking_id,
                "appointment": record,
                "message": f"Successfully confirmed and scheduled {department} appointment for {date_str} at {slot_time}.",
            },
            execution_latency_ms=round((time.time() - t0) * 1000, 2),
        )


# Registry of available tools
TOOL_REGISTRY: Dict[str, BaseAgentTool] = {
    SearchApprovedDocumentsTool.name: SearchApprovedDocumentsTool(),
    CheckAppointmentAvailabilityTool.name: CheckAppointmentAvailabilityTool(),
    RequestSupervisedPredictionTool.name: RequestSupervisedPredictionTool(),
    RetrieveClusterSummariesTool.name: RetrieveClusterSummariesTool(),
    ScheduleMockAppointmentTool.name: ScheduleMockAppointmentTool(),
}


def get_tool(tool_name: str) -> Optional[BaseAgentTool]:
    return TOOL_REGISTRY.get(tool_name)


def list_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "is_write_tool": t.is_write_tool,
            "required_role": t.required_role,
        }
        for t in TOOL_REGISTRY.values()
    ]


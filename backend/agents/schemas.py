"""Typed Pydantic Schemas for Structured Agent Generation & Tools (Week 5).

Guarantees strict contract validation, explicit typing, and bounded retries.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class CitationItem(BaseModel):
    doc_name: str = Field(..., description="Filename of the cited clinic policy document")
    version: str = Field(default="1.0.0", description="Policy semver version")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="RRF retrieval score")


class ToolCallRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the typed tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Typed arguments matching tool schema")
    idempotency_key: Optional[str] = Field(None, description="UUID or unique token preventing duplicate mutations")
    requires_confirmation: bool = Field(default=False, description="Whether tool requires explicit user confirmation")


class ToolExecutionResult(BaseModel):
    tool_name: str
    status: Literal["success", "denied", "failed", "confirmation_required"]
    result_data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    execution_latency_ms: float = 0.0


class StructuredAgentResponse(BaseModel):
    session_id: str = Field(default="default_session", description="Conversation session UUID")
    intent: Literal[
        "policy_inquiry",
        "appointment_booking",
        "ml_prediction",
        "patient_clustering",
        "general_administrative",
        "refusal",
    ] = Field(..., description="Classified intent of the interaction")
    status: Literal[
        "completed",
        "needs_confirmation",
        "needs_tool_execution",
        "refused",
        "error",
    ] = Field(default="completed", description="Execution lifecycle status")
    thought_process: str = Field(default="", max_length=1000, description="Internal reasoning trace (bounded)")
    answer: str = Field(..., min_length=1, description="Structured human-facing response")
    citations: List[CitationItem] = Field(default_factory=list, description="Grounding source citations")
    confidence_score: float = Field(default=0.9, ge=0.0, le=1.0, description="Confidence in the response accuracy")
    tool_calls: List[ToolCallRequest] = Field(default_factory=list, description="Requested tool calls")
    tool_results: List[ToolExecutionResult] = Field(default_factory=list, description="Results of tool executions")
    
    # Token Budget Accounting
    prompt_tokens_used: int = Field(default=0, ge=0)
    completion_tokens_used: int = Field(default=0, ge=0)
    total_tokens_used: int = Field(default=0, ge=0)
    budget_remaining_tokens: int = Field(default=2000, ge=0)
    
    # Audit & Resilience Metadata
    validation_attempts: int = Field(default=1, ge=1, le=5)
    redacted_entities_count: int = Field(default=0, ge=0)
    safety_flag: bool = Field(default=False)
    safety_reason: Optional[str] = None

    @field_validator("confidence_score")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, round(v, 3)))


class AppointmentBookingRequest(BaseModel):
    department: str = Field(..., min_length=2, max_length=50)
    preferred_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD")
    slot_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM in 24h format")
    reason: str = Field(..., min_length=3, max_length=200)
    human_confirmation: bool = Field(default=False, description="Explicit human confirmation flag")
    idempotency_key: str = Field(..., min_length=8, description="Unique transaction idempotency key")


class ValidationErrorReport(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    remediation_hint: Optional[str] = None


"""REST API Endpoints for Controlled AI Agents & Structured LLM Generation (Week 5 Phase 2)."""
from __future__ import annotations

import uuid
from typing import Any, Dict

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import CookieJWTAuthentication
from accounts.permissions import IsAdminRole, IsStandardUser
from agents.schemas import StructuredAgentResponse, ValidationErrorReport
from agents.session_manager import get_session_manager
from agents.structured_llm import run_structured_generation, validate_and_parse_response

AGENTS_TAG = "Controlled AI Agents (Week 5)"

CSRF_HEADER = OpenApiParameter(
    name="X-CSRFToken",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=True,
    description="CSRF token from GET /api/auth/csrf.",
)

UNAUTHENTICATED = OpenApiResponse(description="Not signed in or session expired.")
FORBIDDEN = OpenApiResponse(description="Forbidden: access denied for this role.")
UNAVAILABLE = OpenApiResponse(description="Agent service or model unavailable.")


class AgentChatView(APIView):
    """POST /api/v1/agents/chat/ – multi-turn structured conversation with schema validation."""

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsStandardUser | IsAdminRole]
    parser_classes = [JSONParser]

    @extend_schema(
        summary="Structured Agent multi-turn chat with schema validation",
        description=(
            "Accepts a natural language query, validates token budget, detects prompt injection/PHI, "
            "retrieves grounded clinic policy passages, and returns a strictly schema-validated "
            "StructuredAgentResponse with citations and token accounting."
        ),
        tags=[AGENTS_TAG],
        parameters=[CSRF_HEADER],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Structured agent response."),
            400: OpenApiResponse(description="Invalid request payload."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
            503: UNAVAILABLE,
        },
    )
    def post(self, request):
        data = request.data or {}
        query = str(data.get("query", "")).strip()
        if not query:
            return Response({"detail": "The 'query' field is required."}, status=status.HTTP_400_BAD_REQUEST)

        session_id = str(data.get("session_id") or uuid.uuid4())
        filter_metadata = data.get("filter_metadata")
        max_retries = int(data.get("max_retries", 3))

        try:
            structured_resp = run_structured_generation(
                query=query,
                session_id=session_id,
                max_retries=max_retries,
                filter_metadata=filter_metadata,
            )
            return Response(structured_resp.model_dump())
        except Exception as e:
            return Response({"detail": f"Agent generation error: {e}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class SessionDetailView(APIView):
    """GET/DELETE /api/v1/agents/sessions/<session_id>/ – manage conversation session state."""

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsStandardUser | IsAdminRole]

    @extend_schema(
        summary="Retrieve conversation session history and token usage",
        tags=[AGENTS_TAG],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Session state."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
        },
    )
    def get(self, request, session_id):
        session_mgr = get_session_manager()
        session = session_mgr.get_or_create_session(session_id, user_id=str(request.user.id))
        return Response({
            "session_id": session.session_id,
            "turns_count": len(session.turns),
            "summary": session.summary,
            "turns": [
                {
                    "role": t.role,
                    "content": t.content,
                    "tokens": t.tokens,
                    "timestamp": t.timestamp,
                }
                for t in session.turns
            ],
            "total_lifetime_tokens": session.total_lifetime_tokens,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        })

    @extend_schema(
        summary="Clear and reset a conversation session",
        tags=[AGENTS_TAG],
        parameters=[CSRF_HEADER],
        responses={
            200: OpenApiResponse(description="Session cleared."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
        },
    )
    def delete(self, request, session_id):
        session_mgr = get_session_manager()
        cleared = session_mgr.clear_session(session_id)
        return Response({"status": "success", "session_id": session_id, "cleared": cleared})


class SchemaValidationUtilityView(APIView):
    """POST /api/v1/agents/validate-schema/ – test schema validation and error feedback."""

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsStandardUser | IsAdminRole]
    parser_classes = [JSONParser]

    @extend_schema(
        summary="Validate raw payload against StructuredAgentResponse schema",
        tags=[AGENTS_TAG],
        parameters=[CSRF_HEADER],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Validation report."),
            400: OpenApiResponse(description="Invalid request."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
        },
    )
    def post(self, request):
        data = request.data or {}
        raw_text = data.get("raw_text")
        if not raw_text:
            return Response({"detail": "'raw_text' is required."}, status=status.HTTP_400_BAD_REQUEST)

        parsed, errors = validate_and_parse_response(raw_text, StructuredAgentResponse)
        report = ValidationErrorReport(
            is_valid=(parsed is not None),
            errors=errors,
            remediation_hint=(
                "Output strictly adheres to StructuredAgentResponse."
                if parsed is not None
                else "Provide missing required fields or fix type mismatches."
            ),
        )
        return Response(report.model_dump())

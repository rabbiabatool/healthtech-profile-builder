"""Views for the LLM Policy FAQ assistant endpoint.

POST /api/v1/llm/faq  – member-only, JWT cookie auth, CSRF-protected.
GET  /api/v1/llm/faq/evaluate – member-only, runs the 12-case evaluation harness.
"""
import json
import os

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response

from accounts.authentication import CookieJWTAuthentication
from accounts.permissions import IsStandardUser
from predictions.views import MemberMLBaseView

FAQ_TAG = "Policy FAQ (educational LLM)"

CSRF_HEADER = OpenApiParameter(
    name="X-CSRFToken",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=True,
    description="CSRF token from GET /api/auth/csrf.",
)

UNAUTHENTICATED = OpenApiResponse(description="Not signed in, or the session or token has expired.")
FORBIDDEN = OpenApiResponse(description="Not allowed: wrong role or missing CSRF token.")
UNAVAILABLE = OpenApiResponse(description="The RAG engine failed to load policy documents.")


def _unavailable(error):
    return Response({"detail": str(error)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


def _bad_request(msg):
    return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)


class PolicyFAQView(MemberMLBaseView):
    """POST /api/v1/llm/faq – ask a question answered by clinic policy documents."""

    parser_classes = [JSONParser]

    @extend_schema(
        summary="Ask the Greenleaf Clinic Policy FAQ assistant",
        description=(
            "Retrieval-Augmented Generation (RAG) over approved fictional clinic policy documents. "
            "Returns a structured JSON answer with cited source passages, confidence level, "
            "out-of-scope flag, and safety flag. Medical questions and adversarial prompt injection "
            "are refused. No patient-identifiable data is processed or sent to any external LLM. "
            "Educational prototype only — not medical advice."
        ),
        tags=[FAQ_TAG],
        parameters=[CSRF_HEADER],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Structured FAQ answer with citations."),
            400: OpenApiResponse(description="Missing or empty question field."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
            503: UNAVAILABLE,
        },
    )
    def post(self, request):
        question = (request.data or {}).get("question", "").strip()
        if not question:
            return _bad_request("The 'question' field is required and must not be empty.")
        if len(question) > 1000:
            return _bad_request("Question must be at most 1000 characters.")

        api_key = os.environ.get("GEMINI_API_KEY", "GEMINI_API_KEY_NOT_SET")

        try:
            from rag.engine import answer_question
            result = answer_question(
                question=question,
                top_k=3,
                temperature=0.2,
                max_output_tokens=512,
                api_key=api_key,
            )
        except Exception as e:
            return _unavailable(f"RAG engine error: {e}")

        return Response(result)


class PolicyFAQEvaluateView(MemberMLBaseView):
    """GET /api/v1/llm/faq/evaluate – run the 12-case evaluation harness."""

    @extend_schema(
        summary="Run the 12-case LLM FAQ evaluation harness",
        description=(
            "Executes all 12 pre-defined evaluation prompts (answerable, ambiguous, out-of-scope, "
            "medical, and adversarial prompt injection) and returns a structured pass/fail matrix "
            "with citation quality, confidence levels, and token estimates."
        ),
        tags=[FAQ_TAG],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="12-case evaluation matrix."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
            503: UNAVAILABLE,
        },
    )
    def get(self, request):
        api_key = os.environ.get("GEMINI_API_KEY", "GEMINI_API_KEY_NOT_SET")
        try:
            from rag.evaluation import run_evaluation, _write_eval_markdown
            from pathlib import Path
            report = run_evaluation(api_key=api_key)
            # Also persist the markdown report
            out_path = Path(__file__).resolve().parent.parent.parent / "docs" / "ml" / "LLM_EVALUATION.md"
            _write_eval_markdown(report, out_path)
            return Response(report)
        except Exception as e:
            return _unavailable(f"Evaluation harness error: {e}")


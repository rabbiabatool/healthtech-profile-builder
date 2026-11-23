"""Views for the LLM Policy FAQ assistant endpoint and policy ingestion management.

POST /api/v1/llm/faq                  – member-only, JWT cookie auth, CSRF-protected.
GET  /api/v1/llm/faq/evaluate         – member-only, runs comparative 12-case evaluation harness.
GET  /api/v1/llm/policies             – authenticated members & admins list approved/pending policies.
POST /api/v1/llm/policies             – ADMIN-only, upload new policy document (starts PENDING).
POST /api/v1/llm/policies/<name>/approve – ADMIN-only, approve policy document for indexing.
"""
from __future__ import annotations

import os
from pathlib import Path

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import AdminSessionAuthentication, CookieJWTAuthentication
from accounts.permissions import IsAdminRole
from predictions.views import MemberMLBaseView
from rag.engine import (
    GENERIC_UNAVAILABLE_MESSAGE,
    RateLimitExceeded,
    answer_question,
    get_policy_registry,
)

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
UNAVAILABLE = OpenApiResponse(description="The RAG engine or provider is temporarily unavailable.")


def _unavailable(msg: str = GENERIC_UNAVAILABLE_MESSAGE):
    return Response({"detail": msg}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


def _bad_request(msg: str):
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
            result = answer_question(
                question=question,
                top_k=3,
                temperature=0.2,
                max_output_tokens=512,
                api_key=api_key,
            )
        except RateLimitExceeded as e:
            return Response(
                {"detail": str(e), "error_code": "RATE_LIMIT_EXCEEDED"},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": "1"},
            )
        except Exception:
            return _unavailable(GENERIC_UNAVAILABLE_MESSAGE)

        if result.get("answer") == GENERIC_UNAVAILABLE_MESSAGE:
            return Response(result, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(result)


class PolicyFAQEvaluateView(APIView):
    """GET /api/v1/llm/faq/evaluate – Read-only retrieval of existing evaluation report.
       POST /api/v1/llm/faq/evaluate – Admin-only evaluation execution (CSRF protected)."""

    authentication_classes = [AdminSessionAuthentication, CookieJWTAuthentication]
    parser_classes = [JSONParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminRole()]
        return [AllowAny()]

    @extend_schema(
        summary="Retrieve existing LLM FAQ evaluation report (Read-Only)",
        description=(
            "Retrieves the existing saved evaluation report. Does NOT run the evaluation runner "
            "or rewrite disk artifacts. Open to authenticated members and admins."
        ),
        tags=[FAQ_TAG],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Saved evaluation report."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
            404: OpenApiResponse(description="No evaluation report has been generated yet."),
        },
    )
    def get(self, request):
        report_json_path = Path(__file__).resolve().parent.parent.parent / "docs" / "ml" / "LLM_EVALUATION.json"
        if report_json_path.exists():
            try:
                import json
                with open(report_json_path, "r", encoding="utf-8") as f:
                    report = json.load(f)
                return Response(report)
            except Exception:
                pass

        report_md_path = Path(__file__).resolve().parent.parent.parent / "docs" / "ml" / "LLM_EVALUATION.md"
        if report_md_path.exists():
            return Response({
                "status": "available",
                "report_format": "markdown",
                "message": "Evaluation report markdown exists on disk. An admin can trigger POST to refresh.",
            })

        return Response(
            {"detail": "No evaluation report available. An administrator must trigger POST to run evaluation."},
            status=status.HTTP_404_NOT_FOUND,
        )

    @extend_schema(
        summary="Execute the comparative evaluation harness (Admin Only)",
        description=(
            "ADMIN-ONLY: Executes evaluation prompts across retrieval settings and regenerates "
            "the evaluation report. Requires admin session authentication and CSRF token."
        ),
        tags=[FAQ_TAG],
        parameters=[CSRF_HEADER],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="12-case evaluation matrix."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
            503: UNAVAILABLE,
        },
    )
    def post(self, request):
        data = request.data or {}
        dry_run = bool(data.get("dry_run", False) or data.get("offline", False))
        api_key = "GEMINI_API_KEY_NOT_SET" if dry_run else os.environ.get("GEMINI_API_KEY", "GEMINI_API_KEY_NOT_SET")
        try:
            import json
            from rag.evaluation import run_comparative_retrieval_evaluation, _write_eval_markdown
            comp = run_comparative_retrieval_evaluation(api_key=api_key)
            strict_rep = comp.get("strict", {})
            relaxed_rep = comp.get("relaxed", {})
            docs_dir = Path(__file__).resolve().parent.parent.parent / "docs" / "ml"
            out_path = docs_dir / "LLM_EVALUATION.md"
            json_path = docs_dir / "LLM_EVALUATION.json"
            if isinstance(strict_rep, dict) and "results" in strict_rep:
                try:
                    _write_eval_markdown(strict_rep, out_path, relaxed_report=relaxed_rep)
                except Exception:
                    pass
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(comp, f, indent=2)
            except Exception:
                pass
            return Response(comp)
        except Exception as e:
            return _unavailable(f"Evaluation harness execution error: {e}")


# ──────────────────────────────────────────────────────────
# Policy Ingestion and Governance Endpoints
# ──────────────────────────────────────────────────────────

class PolicyDocumentListView(APIView):
    """GET /api/v1/llm/policies – List policies; POST /api/v1/llm/policies – Upload (Admin only)."""

    authentication_classes = [AdminSessionAuthentication, CookieJWTAuthentication]
    parser_classes = [JSONParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminRole()]
        return [IsAuthenticated()]

    def get(self, request):
        """List registered policy documents."""
        registry = get_policy_registry()
        docs = registry.list_documents()
        return Response({"policies": docs})

    def post(self, request):
        """Admin-only policy document upload (starts PENDING)."""
        data = request.data or {}
        doc_name = (data.get("doc_name") or "").strip()
        content = (data.get("content") or "").strip()

        if not doc_name:
            return _bad_request("The 'doc_name' field is required.")
        if not content:
            return _bad_request("The 'content' field is required.")
        if len(content) < 20:
            return _bad_request("Policy content must be at least 20 characters.")

        registry = get_policy_registry()
        uploaded_by = getattr(request.user, "email", "admin")
        doc = registry.upload_document(doc_name=doc_name, content=content, uploaded_by=uploaded_by)

        return Response({
            "message": f"Policy '{doc.doc_name}' uploaded successfully. Status: PENDING approval.",
            "doc_name": doc.doc_name,
            "status": doc.status,
            "uploaded_by": doc.uploaded_by,
        }, status=status.HTTP_201_CREATED)


class PolicyDocumentApproveView(APIView):
    """POST /api/v1/llm/policies/<str:doc_name>/approve – Admin-only approval."""

    authentication_classes = [AdminSessionAuthentication, CookieJWTAuthentication]
    permission_classes = [IsAdminRole]
    parser_classes = [JSONParser]

    def post(self, request, doc_name: str):
        registry = get_policy_registry()
        clean_name = doc_name if doc_name.endswith(".txt") else f"{doc_name}.txt"

        if clean_name not in registry.documents:
            return Response(
                {"detail": f"Policy document '{clean_name}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        approved_by = getattr(request.user, "email", "admin")
        doc = registry.approve_document(clean_name, approved_by=approved_by)

        return Response({
            "message": f"Policy '{doc.doc_name}' approved and re-indexed into vector store.",
            "doc_name": doc.doc_name,
            "status": doc.status,
            "approved_by": doc.approved_by,
        })


class PolicyDocumentRevokeView(APIView):
    """POST /api/v1/llm/policies/<str:doc_name>/revoke – Admin-only revocation."""

    authentication_classes = [AdminSessionAuthentication, CookieJWTAuthentication]
    permission_classes = [IsAdminRole]
    parser_classes = [JSONParser]

    def post(self, request, doc_name: str):
        registry = get_policy_registry()
        clean_name = doc_name if doc_name.endswith(".txt") else f"{doc_name}.txt"
        try:
            revoked_by = getattr(request.user, "email", "admin")
            doc = registry.revoke_document(clean_name, revoked_by=revoked_by)
            return Response({
                "message": f"Policy '{doc.doc_name}' revoked successfully.",
                "doc_name": doc.doc_name,
                "status": doc.status,
                "revoked_by": doc.revoked_by,
            })
        except KeyError:
            return Response(
                {"detail": f"Policy document '{clean_name}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

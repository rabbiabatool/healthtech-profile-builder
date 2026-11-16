"""Views for the LLM Policy FAQ assistant endpoint.

POST /api/v1/llm/faq  – member-only, JWT cookie auth, CSRF-protected.
GET  /api/v1/llm/faq/evaluate – member-only, runs the 12-case evaluation harness.
POST /api/v1/llm/rag/search – member-only, hybrid BM25 + TF-IDF with metadata filters.
GET  /api/v1/llm/rag/eval-20 – member-only, runs 20-question retrieval benchmark.
POST /api/v1/llm/rag/documents – member-only, dynamic add/update/delete re-indexing.
"""
import os
from pathlib import Path

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response

from accounts.permissions import IsAdminRole, IsStandardUser
from predictions.views import MemberMLBaseView

FAQ_TAG = "Policy FAQ (educational LLM)"
ADVANCED_RAG_TAG = "Advanced RAG & Evaluation (Week 5)"

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
            report = run_evaluation(api_key=api_key)
            out_path = Path(__file__).resolve().parent.parent.parent / "docs" / "ml" / "LLM_EVALUATION.md"
            _write_eval_markdown(report, out_path)
            return Response(report)
        except Exception as e:
            return _unavailable(f"Evaluation harness error: {e}")


class AdvancedRAGSearchView(MemberMLBaseView):
    """POST /api/v1/llm/rag/search – hybrid BM25 + TF-IDF retrieval with metadata filtering."""

    permission_classes = [IsStandardUser | IsAdminRole]

    parser_classes = [JSONParser]

    @extend_schema(
        summary="Advanced hybrid retrieval with metadata filtering",
        description=(
            "Performs hybrid retrieval over clinic policy chunks combining BM25 keyword ranking and "
            "TF-IDF cosine similarity using Reciprocal Rank Fusion (RRF). Supports metadata pre-filters "
            "(category, department, audience)."
        ),
        tags=[ADVANCED_RAG_TAG],
        parameters=[CSRF_HEADER],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Ranked passages with RRF scores."),
            400: OpenApiResponse(description="Invalid search parameters."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
            503: UNAVAILABLE,
        },
    )
    def post(self, request):
        data = request.data or {}
        query = str(data.get("query", "")).strip()
        if not query:
            return _bad_request("The 'query' parameter is required.")

        top_k = min(10, max(1, int(data.get("top_k", 3))))
        filter_metadata = data.get("filter_metadata")
        if filter_metadata is not None and not isinstance(filter_metadata, dict):
            return _bad_request("'filter_metadata' must be a JSON dictionary.")

        try:
            from rag.advanced_engine import get_advanced_store
            store = get_advanced_store()
            passages = store.retrieve_hybrid(
                query=query,
                top_k=top_k,
                filter_metadata=filter_metadata,
            )
            return Response({
                "query": query,
                "top_k": top_k,
                "filter_metadata": filter_metadata,
                "total_passages_found": len(passages),
                "passages": passages,
            })
        except Exception as e:
            return _unavailable(f"Hybrid retrieval error: {e}")


class AdvancedRAGEval20View(MemberMLBaseView):
    """GET /api/v1/llm/rag/eval-20 – run 20-question retrieval benchmark."""

    permission_classes = [IsStandardUser | IsAdminRole]

    @extend_schema(
        summary="Run the 20-question retrieval evaluation benchmark",
        description=(
            "Evaluates retrieval performance isolated from generation across 20 labeled queries. "
            "Reports Recall@1, Recall@3, Recall@5, Hit Rate, Groundedness, and Abstention accuracy, "
            "comparing Baseline TF-IDF vs Advanced Hybrid BM25+TF-IDF RRF."
        ),
        tags=[ADVANCED_RAG_TAG],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Comparative retrieval report."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
            503: UNAVAILABLE,
        },
    )
    def get(self, request):
        try:
            from rag.advanced_evaluation import run_comparative_rag_benchmark, write_evaluation_markdown
            benchmark_report = run_comparative_rag_benchmark()
            out_path = Path(__file__).resolve().parent.parent.parent / "docs" / "ml" / "RAG_ADVANCED_EVALUATION.md"
            write_evaluation_markdown(benchmark_report, out_path)
            return Response(benchmark_report)
        except Exception as e:
            return _unavailable(f"Retrieval benchmark error: {e}")


class DocumentManagementView(MemberMLBaseView):
    """POST /api/v1/llm/rag/documents – dynamic add/update/delete re-indexing."""

    permission_classes = [IsAdminRole]

    parser_classes = [JSONParser]

    @extend_schema(
        summary="Manage documents and trigger real-time re-indexing",
        description=(
            "Add, update, or soft-delete policy documents in the active index. Immediately rebuilds "
            "lexical and semantic representations without service restart."
        ),
        tags=[ADVANCED_RAG_TAG],
        parameters=[CSRF_HEADER],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Updated document catalog."),
            400: OpenApiResponse(description="Invalid document payload."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
            503: UNAVAILABLE,
        },
    )
    def post(self, request):
        data = request.data or {}
        action = data.get("action", "").lower()
        if action not in {"add", "update", "delete", "reindex"}:
            return _bad_request("Action must be one of: 'add', 'update', 'delete', 'reindex'.")

        try:
            from rag.advanced_engine import DocumentMetadata, PolicyDocument, get_advanced_store
            store = get_advanced_store()

            if action == "reindex":
                chunks_indexed = store.reindex()
                return Response({"status": "success", "action": "reindex", "total_chunks": chunks_indexed})

            doc_id = str(data.get("doc_id", "")).strip()
            if not doc_id:
                return _bad_request("'doc_id' is required for this action.")

            if action == "add":
                doc_name = str(data.get("doc_name", f"{doc_id}.txt")).strip()
                content = str(data.get("content", "")).strip()
                version = str(data.get("version", "1.0.0")).strip()
                if not content:
                    return _bad_request("'content' is required when adding a document.")
                meta_raw = data.get("metadata", {})
                metadata = DocumentMetadata(
                    category=meta_raw.get("category", "general"),
                    department=meta_raw.get("department", "general"),
                    target_audience=meta_raw.get("target_audience", "all"),
                    effective_date=meta_raw.get("effective_date", "2026-01-01"),
                )
                new_doc = PolicyDocument(
                    doc_id=doc_id,
                    doc_name=doc_name,
                    version=version,
                    content=content,
                    metadata=metadata,
                )
                store.add_document(new_doc)
                return Response({"status": "success", "action": "add", "doc_id": doc_id, "version": version})

            elif action == "update":
                content = str(data.get("content", "")).strip()
                if not content:
                    return _bad_request("'content' is required when updating a document.")
                version = data.get("version")
                success = store.update_document(doc_id=doc_id, content=content, version=version)
                if not success:
                    return _bad_request(f"Document with id '{doc_id}' not found.")
                return Response({"status": "success", "action": "update", "doc_id": doc_id})

            elif action == "delete":
                soft = bool(data.get("soft", True))
                success = store.delete_document(doc_id=doc_id, soft=soft)
                if not success:
                    return _bad_request(f"Document with id '{doc_id}' not found.")
                return Response({"status": "success", "action": "delete", "doc_id": doc_id, "soft": soft})

        except Exception as e:
            return _unavailable(f"Document management error: {e}")

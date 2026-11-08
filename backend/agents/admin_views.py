"""Admin Audit Dashboard & Background Job Management Endpoints (Week 5 Phase 4).

Surfaces agent action traces, write approval decisions, retrieval sources, background job
execution telemetry, and synthetic model drift monitoring.
"""
from __future__ import annotations

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import CookieJWTAuthentication
from accounts.permissions import IsAdminRole, IsStandardUser
from agents.monitoring import get_model_monitor
from agents.task_queue import get_task_queue
from rag.advanced_engine import get_advanced_store

ADMIN_TAG = "Agent Audit & Operations (Week 5)"

CSRF_HEADER = OpenApiParameter(
    name="X-CSRFToken",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=True,
    description="CSRF token from GET /api/auth/csrf.",
)

UNAUTHENTICATED = OpenApiResponse(description="Not signed in or session expired.")
FORBIDDEN = OpenApiResponse(description="Forbidden: access denied for this role.")


class AdminAuditDashboardView(APIView):
    """GET /api/v1/agents/admin/audit/ – unified administrative audit dashboard."""

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminRole]

    @extend_schema(
        summary="Unified admin audit dashboard for agent workflows, jobs, and drift telemetry",
        description=(
            "Aggregates agent action traces, write approval decisions, policy retrieval sources, "
            "background job statuses with retry counters, and model monitoring drift statistics."
        ),
        tags=[ADMIN_TAG],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Comprehensive audit payload."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
        },
    )
    def get(self, request):
        queue = get_task_queue()
        monitor = get_model_monitor()
        store = get_advanced_store()

        recent_jobs = queue.list_jobs(limit=10)
        drift_report = monitor.evaluate_drift()

        # Audit of active policy documents & versioning
        active_docs = [
            {
                "doc_id": d.doc_id,
                "doc_name": d.doc_name,
                "version": d.version,
                "category": d.metadata.category,
                "department": d.metadata.department,
                "sha256": d.sha256[:16] + "...",
                "is_active": d.is_active,
                "updated_at": d.updated_at,
            }
            for d in store.documents.values()
        ]

        # Audit of approval and write protection decisions
        from agents.tools import _MOCK_APPOINTMENTS_STORE
        scheduled_writes = list(_MOCK_APPOINTMENTS_STORE.values())

        return Response({
            "status": "active",
            "active_documents": active_docs,
            "total_chunks_in_store": len(store.chunks),
            "background_jobs": recent_jobs,
            "scheduled_writes_audit": scheduled_writes[-10:],
            "model_monitoring": drift_report,
            "registered_model_versions": [
                {"version": "v1.0.0-supervised", "algorithm": "Logistic Regression / Random Forest", "status": "ACTIVE_PRODUCTION"},
                {"version": "v1.0.0-clustering", "algorithm": "K-Means (k=6) + Agglomerative", "status": "ACTIVE_PRODUCTION"},
                {"version": "v2.0.0-hybrid-rag", "algorithm": "BM25 + TF-IDF RRF", "status": "ACTIVE_PRODUCTION"},
            ],
        })


class TaskJobSubmitView(APIView):
    """POST /api/v1/agents/jobs/ – submit async background indexing or batch prediction task."""

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsStandardUser | IsAdminRole]
    parser_classes = [JSONParser]

    @extend_schema(
        summary="Submit an asynchronous background task",
        tags=[ADMIN_TAG],
        parameters=[CSRF_HEADER],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Queued task job."),
            400: OpenApiResponse(description="Invalid job parameters."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
        },
    )
    def post(self, request):
        data = request.data or {}
        job_type = str(data.get("job_type", "")).strip()
        if job_type not in ["document_indexing", "batch_predictions"]:
            return Response(
                {"detail": "Invalid 'job_type'. Must be 'document_indexing' or 'batch_predictions'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = data.get("payload", {})
        max_retries = int(data.get("max_retries", 3))
        run_sync = bool(data.get("run_sync", False))

        queue = get_task_queue()
        job = queue.submit_job(job_type=job_type, payload=payload, max_retries=max_retries, run_sync=run_sync)

        from dataclasses import asdict
        return Response(asdict(job))


class TaskJobDetailView(APIView):
    """GET /api/v1/agents/jobs/<job_id>/ – inspect background job status, retries, and result."""

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsStandardUser | IsAdminRole]

    @extend_schema(
        summary="Inspect background job status and results",
        tags=[ADMIN_TAG],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Task job status."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
            404: OpenApiResponse(description="Job not found."),
        },
    )
    def get(self, request, job_id):
        queue = get_task_queue()
        job = queue.get_job(job_id)
        if not job:
            return Response({"detail": f"Job '{job_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

        from dataclasses import asdict
        return Response(asdict(job))


class TaskJobListView(APIView):
    """GET /api/v1/agents/jobs/ – list recent background jobs."""

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsStandardUser | IsAdminRole]

    @extend_schema(
        summary="List recent background task queue jobs",
        tags=[ADMIN_TAG],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="List of task jobs."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
        },
    )
    def get(self, request):
        queue = get_task_queue()
        return Response({"jobs": queue.list_jobs(limit=25)})


class ModelMonitoringMetricsView(APIView):
    """GET /api/v1/agents/monitoring/metrics/ – telemetry and KS statistical drift report."""

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsStandardUser | IsAdminRole]

    @extend_schema(
        summary="Retrieve synthetic prediction drift metrics and latency percentiles",
        tags=[ADMIN_TAG],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Monitoring report."),
            401: UNAUTHENTICATED,
            403: FORBIDDEN,
        },
    )
    def get(self, request):
        monitor = get_model_monitor()
        return Response(monitor.evaluate_drift())


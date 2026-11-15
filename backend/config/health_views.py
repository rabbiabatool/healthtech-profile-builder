"""Health, Readiness, and Observability Endpoints (Week 6 Final Capstone).

Provides Kubernetes/Docker-compatible liveness (/health), readiness (/ready),
and system status checks with database and ML model verification.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from django.db import connection
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from mlcore.registry import load_model, ModelUnavailable
from rag.advanced_engine import get_advanced_store

HEALTH_TAG = "System Health & Observability (Week 6)"


class HealthCheckView(APIView):
    """GET /health – Liveness probe verifying the API server is up."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Liveness check (Kubernetes / Docker health check)",
        description="Returns HTTP 200 if the web process is running and accepting HTTP traffic.",
        tags=[HEALTH_TAG],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Server is alive."),
        },
    )
    def get(self, request):
        return Response(
            {
                "status": "pass",
                "service": "healthtech-backend",
                "version": "6.0.0-capstone",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime": "operational",
            },
            status=status.HTTP_200_OK,
        )


class ReadinessCheckView(APIView):
    """GET /ready – Readiness probe verifying DB, ML Model, and RAG store."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Readiness check (Dependencies & Model integrity)",
        description=(
            "Verifies operational readiness: database connectivity, ML model artifact integrity, "
            "and RAG document store indexing."
        ),
        tags=[HEALTH_TAG],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="All core dependencies are ready."),
            503: OpenApiResponse(response=OpenApiTypes.OBJECT, description="One or more critical dependencies unavailable."),
        },
    )
    def get(self, request):
        checks = {}
        all_ready = True

        # 1. Database check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            checks["database"] = {"status": "pass", "details": "Database connection verified"}
        except Exception as exc:
            checks["database"] = {"status": "fail", "details": str(exc)}
            all_ready = False

        # 2. ML Model check
        try:
            metadata, _ = load_model()
            checks["ml_model"] = {
                "status": "pass",
                "version": metadata.get("version", "unknown"),
                "algorithm": metadata.get("algorithm", "Logistic Regression"),
            }
        except ModelUnavailable as exc:
            checks["ml_model"] = {"status": "warn", "details": f"Model unavailable: {exc}"}
        except Exception as exc:
            checks["ml_model"] = {"status": "warn", "details": str(exc)}

        # 3. RAG Store check
        try:
            store = get_advanced_store()
            checks["rag_store"] = {
                "status": "pass",
                "indexed_documents": len(store.documents),
                "indexed_chunks": len(store.chunks),
            }
        except Exception as exc:
            checks["rag_store"] = {"status": "warn", "details": str(exc)}

        resp_status = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(
            {
                "status": "pass" if all_ready else "fail",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checks": checks,
            },
            status=resp_status,
        )

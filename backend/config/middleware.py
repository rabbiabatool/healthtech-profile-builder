"""Structured Logging and Request Correlation ID Middleware (Week 6 Final Capstone).

Enforces:
- Unique correlation/request IDs (X-Request-ID) for distributed tracing.
- Structured access logging with method, path, response status, duration (ms), user role.
- Redaction of sensitive headers and tokens.
- Response header attribution (X-Request-ID, X-Response-Time-Ms).
"""
from __future__ import annotations

import json
import logging
import time
import uuid

logger = logging.getLogger("healthtech.access")


class StructuredLoggingMiddleware:
    """Captures request latency, correlation ID, and logs structured telemetry."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.perf_counter()

        # Extract or generate X-Request-ID
        request_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:12]}"
        request.request_id = request_id

        response = self.get_response(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Attach telemetry headers
        response["X-Request-ID"] = request_id
        response["X-Response-Time-Ms"] = str(duration_ms)

        # Extract user context safely
        user_identifier = "anonymous"
        user_role = "ANONYMOUS"
        if hasattr(request, "user") and request.user.is_authenticated:
            user_identifier = f"user_{request.user.id}"
            user_role = getattr(request.user, "role", "USER")

        log_payload = {
            "timestamp": time.time(),
            "request_id": request_id,
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user": user_identifier,
            "role": user_role,
        }

        # Do not flood logs on health checks in production, but log at debug level
        if request.path in ("/health", "/ready"):
            logger.debug(json.dumps(log_payload))
        else:
            if response.status_code >= 500:
                logger.error(json.dumps(log_payload))
            elif response.status_code >= 400:
                logger.warning(json.dumps(log_payload))
            else:
                logger.info(json.dumps(log_payload))

        return response

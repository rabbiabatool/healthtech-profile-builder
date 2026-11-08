"""Tests for Week 5 Phase 4: Background Task Queue, Safe Retries, Model Drift Monitoring & Admin Audit."""
import time
from types import SimpleNamespace
import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from agents.admin_views import (
    AdminAuditDashboardView,
    ModelMonitoringMetricsView,
    TaskJobDetailView,
    TaskJobListView,
    TaskJobSubmitView,
)
from agents.monitoring import ModelMonitor, get_model_monitor
from agents.task_queue import BackgroundTaskQueue, get_task_queue


@pytest.fixture
def auth_user():
    return SimpleNamespace(is_authenticated=True, is_active=True, role="USER", email="user@clinic.test", id=1)


@pytest.fixture
def admin_user():
    return SimpleNamespace(is_authenticated=True, is_active=True, role="ADMIN", email="admin@clinic.test", id=2)


# ─── Unit Tests: Background Task Queue & Safe Retries ────────────────────────

def test_task_queue_document_indexing_success():
    queue = BackgroundTaskQueue(max_workers=1)
    job = queue.submit_job(job_type="document_indexing", run_sync=True)
    assert job.status == "succeeded"
    assert job.result is not None
    assert job.result["total_chunks_indexed"] > 0
    assert job.duration_ms > 0
    assert job.retry_count == 0


def test_task_queue_batch_predictions_success():
    queue = BackgroundTaskQueue(max_workers=1)
    job = queue.submit_job(
        job_type="batch_predictions",
        payload={"cohort_size": 50},
        run_sync=True,
    )
    assert job.status == "succeeded"
    assert job.result["cohort_size"] == 50
    assert 0.0 <= job.result["mean_no_show_risk"] <= 1.0
    assert len(job.result["predictions_sample"]) == 10


def test_task_queue_transient_failure_and_safe_retry():
    queue = BackgroundTaskQueue(max_workers=1)
    # Payload simulates transient failure on first attempt, succeeding on retry
    job = queue.submit_job(
        job_type="document_indexing",
        payload={"simulate_transient_failure": True},
        max_retries=3,
        run_sync=True,
    )
    assert job.status == "succeeded"
    assert job.retry_count == 1
    assert job.result is not None


def test_task_queue_permanent_failure_exhausts_retries():
    queue = BackgroundTaskQueue(max_workers=1)
    # Invalid job type triggers permanent ValueError
    job = queue.submit_job(
        job_type="invalid_unknown_job_type",
        max_retries=2,
        run_sync=True,
    )
    assert job.status == "failed"
    assert job.retry_count > 2
    assert "Unknown job type" in job.error


# ─── Unit Tests: Model Monitoring & Statistical Drift Detection ──────────────

def test_model_monitor_records_and_computes_percentiles():
    monitor = ModelMonitor(buffer_size=100)
    for p in [0.12, 0.18, 0.25, 0.35, 0.08, 0.45]:
        monitor.record_prediction(probability=p, latency_ms=3.2, success=True)

    report = monitor.evaluate_drift()
    assert report["model_version"] == "v1.0.0-supervised-logistic"
    assert "drift_analysis" in report
    assert "Two-Sample Kolmogorov-Smirnov" in report["drift_analysis"]["statistical_test"]
    assert 0.0 <= report["drift_analysis"]["ks_statistic"] <= 1.0
    assert report["latency_percentiles"]["p50_ms"] > 0
    assert "clinical" in report["operational_disclaimer"].lower()
    assert "diagnosis" in report["operational_disclaimer"].lower()


def test_model_monitor_detects_distribution_drift():
    monitor = ModelMonitor(buffer_size=500)
    # Inject 150 artificially skewed high probabilities to trigger KS drift
    for _ in range(150):
        monitor.record_prediction(probability=0.88, latency_ms=4.0, success=True)

    report = monitor.evaluate_drift()
    assert report["drift_analysis"]["drift_detected"] is True
    assert report["drift_analysis"]["drift_severity"] == "ELEVATED_LOGISTICAL_SHIFT"


# ─── Integration Tests: Admin Audit & Task Queue REST APIs ───────────────────

@pytest.fixture
def api_client():
    return APIRequestFactory()


def test_api_admin_audit_dashboard_rbac(api_client, auth_user, admin_user):
    view = AdminAuditDashboardView.as_view()

    # Standard User must be denied with 403 Forbidden
    req_user = api_client.get("/api/v1/agents/admin/audit/")
    force_authenticate(req_user, user=auth_user)
    resp_user = view(req_user)
    assert resp_user.status_code == 403

    # Admin User must be granted access (200 OK)
    req_admin = api_client.get("/api/v1/agents/admin/audit/")
    force_authenticate(req_admin, user=admin_user)
    resp_admin = view(req_admin)
    assert resp_admin.status_code == 200
    data = resp_admin.data
    assert "active_documents" in data
    assert "background_jobs" in data
    assert "model_monitoring" in data
    assert len(data["registered_model_versions"]) >= 3


def test_api_task_job_lifecycle(api_client, auth_user):
    view_submit = TaskJobSubmitView.as_view()
    view_detail = TaskJobDetailView.as_view()
    view_list = TaskJobListView.as_view()

    # Submit job
    req_submit = api_client.post(
        "/api/v1/agents/jobs/",
        data={"job_type": "document_indexing", "run_sync": True},
        format="json",
    )
    force_authenticate(req_submit, user=auth_user)
    resp_submit = view_submit(req_submit)
    assert resp_submit.status_code == 200
    job_id = resp_submit.data["job_id"]
    assert resp_submit.data["status"] == "succeeded"

    # Inspect job detail
    req_detail = api_client.get(f"/api/v1/agents/jobs/{job_id}/")
    force_authenticate(req_detail, user=auth_user)
    resp_detail = view_detail(req_detail, job_id=job_id)
    assert resp_detail.status_code == 200
    assert resp_detail.data["job_id"] == job_id

    # List jobs
    req_list = api_client.get("/api/v1/agents/jobs/")
    force_authenticate(req_list, user=auth_user)
    resp_list = view_list(req_list)
    assert resp_list.status_code == 200
    assert len(resp_list.data["jobs"]) >= 1


def test_api_monitoring_metrics_endpoint(api_client, auth_user):
    view = ModelMonitoringMetricsView.as_view()
    req = api_client.get("/api/v1/agents/monitoring/metrics/")
    force_authenticate(req, user=auth_user)
    resp = view(req)
    assert resp.status_code == 200
    assert "drift_analysis" in resp.data
    assert "latency_percentiles" in resp.data

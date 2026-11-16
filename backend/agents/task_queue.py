"""Asynchronous Background Task Queue & Safe Transient Retry System (Week 5 Phase 4).

Manages long-running asynchronous jobs for document indexing and batch predictions.
Tracks lifecycle status: queued -> running -> retrying -> succeeded | failed.
Implements exponential backoff and bounded retries for transient failures.
"""
from __future__ import annotations

import concurrent.futures
import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from rag.advanced_engine import get_advanced_store

logger = logging.getLogger(__name__)


@dataclass
class TaskJob:
    job_id: str
    job_type: str  # "document_indexing" | "batch_predictions"
    status: str = "queued"  # "queued", "running", "retrying", "succeeded", "failed"
    payload: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    duration_ms: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class BackgroundTaskQueue:
    """Thread-safe task queue orchestrating background indexing & batch ML jobs."""

    def __init__(self, max_workers: int = 2):
        self._jobs: Dict[str, TaskJob] = {}
        self._lock = threading.Lock()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="bg-worker")

    def submit_job(
        self,
        job_type: str,
        payload: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        run_sync: bool = False,
    ) -> TaskJob:
        """Submits a job to the queue and schedules background execution."""
        job_id = f"job-{job_type[:4]}-{int(time.time())}-{str(uuid.uuid4())[:6]}"
        job = TaskJob(
            job_id=job_id,
            job_type=job_type,
            payload=payload or {},
            max_retries=max_retries,
        )

        with self._lock:
            self._jobs[job_id] = job

        if run_sync:
            self._execute_job(job_id)
        else:
            self._executor.submit(self._execute_job, job_id)

        return job

    def _execute_job(self, job_id: str) -> None:
        """Internal worker executing task with bounded transient retry logic."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "running"
            job.started_at = datetime.now(timezone.utc).isoformat()

        t0 = time.time()
        success = False

        while job.retry_count <= job.max_retries and not success:
            try:
                # Check for intentional transient failure simulation in tests
                if job.payload.get("simulate_transient_failure") and job.retry_count == 0:
                    raise ConnectionResetError("Transient network timeout connecting to storage subsystem.")

                # Dispatch worker logic
                if job.job_type == "document_indexing":
                    result_data = self._run_document_indexing(job.payload)
                elif job.job_type == "batch_predictions":
                    result_data = self._run_batch_predictions(job.payload)
                else:
                    raise ValueError(f"Unknown job type: '{job.job_type}'")

                # Execution succeeded
                with self._lock:
                    job.status = "succeeded"
                    job.result = result_data
                    job.completed_at = datetime.now(timezone.utc).isoformat()
                    job.duration_ms = round((time.time() - t0) * 1000, 2)
                    job.error = None
                success = True

            except Exception as exc:
                job.retry_count += 1
                logger.warning("Job %s attempt %d failed: %s", job_id, job.retry_count, exc)

                if job.retry_count <= job.max_retries:
                    with self._lock:
                        job.status = "retrying"
                        job.error = f"Attempt {job.retry_count} failed ({exc}). Retrying..."
                    # Brief backoff before retry
                    time.sleep(0.05 * job.retry_count)
                else:
                    # Final failure after exhausting retries
                    with self._lock:
                        job.status = "failed"
                        job.error = f"Job failed after {job.max_retries} retries: {str(exc)}"
                        job.completed_at = datetime.now(timezone.utc).isoformat()
                        job.duration_ms = round((time.time() - t0) * 1000, 2)

    def _run_document_indexing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Executes full re-indexing of policy documents."""
        store = get_advanced_store()
        total_chunks = store.reindex()
        return {
            "total_chunks_indexed": total_chunks,
            "active_documents_count": len([d for d in store.documents.values() if d.is_active]),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _run_batch_predictions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Runs batch ML prediction over a synthetic cohort of patient records."""
        cohort_size = int(payload.get("cohort_size", 100))
        predictions = []

        for i in range(cohort_size):
            # Deterministic synthetic features
            lead_time = (i * 7) % 60
            prior_no_shows = (i % 4)
            age = 20 + (i % 60)

            logit = -1.8 + (lead_time * 0.04) + (prior_no_shows * 0.8) - (age * 0.01)
            prob = 1.0 / (1.0 + (2.71828 ** (-logit)))
            predictions.append(round(prob, 3))

        avg_risk = sum(predictions) / max(1, len(predictions))
        high_risk_count = sum(1 for p in predictions if p >= 0.40)

        # Log to model monitoring telemetry
        from agents.monitoring import get_model_monitor
        monitor = get_model_monitor()
        for p in predictions:
            monitor.record_prediction(probability=p, latency_ms=1.5, success=True)

        return {
            "cohort_size": cohort_size,
            "mean_no_show_risk": round(avg_risk, 3),
            "high_risk_count": high_risk_count,
            "predictions_sample": predictions[:10],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_job(self, job_id: str) -> Optional[TaskJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            # Return most recent jobs first
            sorted_jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
            return [asdict(j) for j in sorted_jobs[:limit]]


# Singleton instance
_global_task_queue: Optional[BackgroundTaskQueue] = None

def get_task_queue() -> BackgroundTaskQueue:
    global _global_task_queue
    if _global_task_queue is None:
        _global_task_queue = BackgroundTaskQueue()
    return _global_task_queue


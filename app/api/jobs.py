"""Job submission and polling endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from app.schemas import JobStatus
from app.worker import celery_app

router = APIRouter()


def submit_task(task_name: str, kwargs: dict[str, object]) -> JobStatus:
    """Enqueue work through the shared Redis-backed Celery broker."""
    task = celery_app.send_task(task_name, kwargs=kwargs, task_id=uuid.uuid4().hex)
    return JobStatus(job_id=task.id, status="queued", progress_pct=0)


def _status(task_id: str) -> JobStatus:
    result = celery_app.AsyncResult(task_id)
    state = result.state
    if state == "SUCCESS":
        return JobStatus(job_id=task_id, status="succeeded", progress_pct=100, result_ref=task_id)
    if state in {"FAILURE", "REVOKED"}:
        return JobStatus(
            job_id=task_id, status="failed", progress_pct=100, error=str(result.result)
        )
    if state in {"STARTED", "PROGRESS"}:
        progress = result.info.get("progress_pct", 10) if isinstance(result.info, dict) else 10
        return JobStatus(job_id=task_id, status="running", progress_pct=progress)
    return JobStatus(job_id=task_id, status="queued", progress_pct=0)


@router.get("/{job_id}", response_model=JobStatus)
def get_job(job_id: str) -> JobStatus:
    if not celery_app.AsyncResult(job_id).id:
        raise HTTPException(status_code=404, detail="job not found")
    return _status(job_id)


@router.get("/{job_id}/result")
def get_result(job_id: str) -> dict[str, object]:
    status = get_job(job_id)
    if status.status != "succeeded":
        raise HTTPException(status_code=409, detail=status.error or "job not complete")
    result = celery_app.AsyncResult(job_id).get(propagate=False)
    if hasattr(result, "model_dump"):
        result = result.model_dump(mode="json")
    return {"ok": True, "data": result}

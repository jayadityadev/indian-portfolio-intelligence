"""Validation / trust report endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.jobs import _status
from app.schemas import TrustReport
from app.worker import celery_app

router = APIRouter()


@router.get("/{job_id}", response_model=TrustReport)
def get_trust_report(job_id: str) -> TrustReport:
    """Return the TrustReport embedded in a completed backtest job's result."""
    status = _status(job_id)
    if status.status != "succeeded":
        raise HTTPException(status_code=409, detail=status.error or "job not complete")
    result = celery_app.AsyncResult(job_id).get(propagate=False)
    if isinstance(result, dict):
        trust = result.get("trust")
        if trust:
            return TrustReport.model_validate(trust)
    raise HTTPException(status_code=404, detail="trust report not found for job")

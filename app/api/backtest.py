"""Backtest submission endpoint."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.jobs import submit_task
from app.schemas import JobStatus, StrategyName

router = APIRouter()


class BacktestRequest(BaseModel):
    symbol: str
    strategy: StrategyName
    params: dict = Field(default_factory=dict)
    start: date | None = None
    end: date | None = None
    net_of_costs: bool = True


@router.post("", response_model=JobStatus)
def submit(request: BacktestRequest) -> JobStatus:
    return submit_task(
        "backtest.run",
        {
            "symbol": request.symbol,
            "strategy": request.strategy,
            "params": request.params,
            "start": request.start.isoformat() if request.start else None,
            "end": request.end.isoformat() if request.end else None,
            "net_of_costs": request.net_of_costs,
        },
    )

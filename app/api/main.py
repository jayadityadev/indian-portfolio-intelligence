"""FastAPI application entrypoint.

Thin orchestration layer only. Routers call services and return ``app.schemas``
shapes. Long-running work is enqueued to Celery and polled via JobStatus.
"""

from fastapi import FastAPI

from app.api import backtest, jobs, market, recommend, regime
from app.config import settings
from app.schemas import HealthResponse

app = FastAPI(
    title="Indian Portfolio Intelligence API",
    version=settings.app_version,
    description="Regime-aware, risk-adjusted, overfitting-controlled strategy "
    "evaluation for Indian equities.",
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(ok=True, version=settings.app_version)


app.include_router(market.router, prefix="/api/v1/market", tags=["market"])
app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["backtest"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(regime.router, prefix="/api/v1/regime", tags=["regime"])
app.include_router(recommend.router, prefix="/api/v1/recommend", tags=["recommend"])

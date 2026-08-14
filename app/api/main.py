"""FastAPI application entrypoint.

Thin orchestration layer only. Routers call services and return ``app.schemas``
shapes. Long-running work is enqueued to Celery and polled via JobStatus.
"""

from fastapi import FastAPI

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


# Routers are mounted as modules are implemented, e.g.:
#   from app.api import backtest, market, recommend, regime, risk
#   app.include_router(market.router, prefix="/api/v1/market", tags=["market"])
#   ...

"""FastAPI application entrypoint.

Thin orchestration layer only. Routers call services and return ``app.schemas``
shapes. Long-running work is enqueued to Celery and polled via JobStatus.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import backtest, jobs, market, recommend, regime, report, risk, validation
from app.config import settings
from app.schemas import HealthResponse

app = FastAPI(
    title="Indian Portfolio Intelligence API",
    version=settings.app_version,
    description="Regime-aware, risk-adjusted, overfitting-controlled strategy "
    "evaluation for Indian equities.",
)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    del request
    detail = exc.detail if isinstance(exc.detail, str) else "request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content={"ok": False, "data": None, "error": {"code": "http_error", "message": detail}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=422,
        content={
            "ok": False,
            "data": None,
            "error": {"code": "validation_error", "message": str(exc.errors())},
        },
    )


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(ok=True, version=settings.app_version)


app.include_router(market.router, prefix="/api/v1/market", tags=["market"])
app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["backtest"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(regime.router, prefix="/api/v1/regime", tags=["regime"])
app.include_router(recommend.router, prefix="/api/v1/recommend", tags=["recommend"])
app.include_router(risk.router, prefix="/api/v1/risk", tags=["risk"])
app.include_router(report.router, prefix="/api/v1/report", tags=["report"])
app.include_router(validation.router, prefix="/api/v1/validation", tags=["validation"])

from datetime import date

from celery import Celery

from app.config import settings

celery_app = Celery("ipi", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=False,
    task_track_started=True,
)


@celery_app.task(name="ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="backtest.run", bind=True)
def run_backtest(
    task: object,
    symbol: str,
    strategy: str,
    params: dict,
    start: str | None = None,
    end: str | None = None,
    net_of_costs: bool = True,
) -> dict:
    """Celery task boundary for long-running backtests."""
    from app.api.deps import load_features
    from app.backtest.engine import run

    features = load_features(symbol)
    if start:
        features = features.loc[features.index.date >= date.fromisoformat(start)]
    if end:
        features = features.loc[features.index.date <= date.fromisoformat(end)]
    result = run(symbol, strategy, params, features, net_of_costs=net_of_costs)  # type: ignore[arg-type]
    return result.model_dump(mode="json")

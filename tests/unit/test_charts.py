import json
from datetime import date, datetime

from app.report.charts import (
    drawdown,
    equity_vs_benchmark,
    price_with_regime,
    strategy_comparison,
    suitability_bars,
    trade_scatter,
)
from app.schemas import (
    BacktestResult,
    CompareReport,
    EquityPoint,
    PerformanceMetrics,
    Recommendation,
    RegimeResult,
    Trade,
)


def _metrics() -> PerformanceMetrics:
    return PerformanceMetrics(
        cagr=0.1,
        total_return_pct=10,
        sharpe=1,
        sortino=1,
        calmar=0.5,
        information_ratio=0.2,
        max_drawdown_pct=20,
        annualized_vol_pct=15,
        win_rate_pct=50,
        profit_factor=1.2,
        avg_win_pct=2,
        avg_loss_pct=1,
        num_trades=1,
        exposure_pct=80,
        benchmark_return_pct=8,
        alpha_pct=2,
        beta=1,
    )


def _result(strategy: str = "ma_crossover") -> BacktestResult:
    points = [
        EquityPoint(date=date(2025, 1, 1), equity=100, benchmark=100),
        EquityPoint(date=date(2025, 1, 2), equity=105, benchmark=102),
    ]
    return BacktestResult(
        symbol="TEST.NS",
        strategy=strategy,
        start=points[0].date,
        end=points[-1].date,
        metrics=_metrics(),
        equity_curve=points,
        trade_list=[
            Trade(
                entry_date=date(2025, 1, 1),
                exit_date=date(2025, 1, 2),
                direction="long",
                pnl_pct=5,
                bars_held=1,
            )
        ],
    )


def test_chart_builders_return_valid_plotly_json() -> None:
    result = _result()
    regime = RegimeResult(
        symbol="TEST.NS",
        method="hmm",
        n_states=3,
        labels=[0, 2],
        state_names={0: "bear", 1: "sideways", 2: "bull"},
        fitted_at=datetime(2025, 1, 1),
    )
    records = [
        {"date": "2025-01-01", "close": 100},
        {"date": "2025-01-02", "close": 105},
    ]
    compare = CompareReport(
        symbol="TEST.NS",
        start=result.start,
        end=result.end,
        results=[result, _result("rsi")],
    )
    recommendation = Recommendation(
        symbol="TEST.NS",
        current_regime={"state_name": "bull", "confidence": 0.8},
        suggested_strategy="momentum",
        rationale=["trend"],
        suitability={"momentum": 0.8, "rsi": 0.3},
        caveat="Not investment advice.",
    )
    charts = [
        price_with_regime(records, regime),
        equity_vs_benchmark(result),
        drawdown(result),
        strategy_comparison(compare),
        suitability_bars(recommendation),
        trade_scatter(result),
    ]
    for chart in charts:
        payload = json.loads(chart)
        assert "data" in payload
        assert "layout" in payload


def test_price_chart_downsamples_long_series() -> None:
    records = [{"date": str(index), "close": index} for index in range(2501)]
    regime = RegimeResult(
        symbol="TEST.NS",
        method="hmm",
        n_states=3,
        labels=[1] * 2501,
        state_names={0: "bear", 1: "sideways", 2: "bull"},
        fitted_at=datetime(2025, 1, 1),
    )
    payload = json.loads(price_with_regime(records, regime))
    assert len(payload["data"][0]["x"]) <= 2000

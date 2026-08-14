from datetime import date, datetime

from app.schemas import (
    BacktestResult,
    EquityPoint,
    PerformanceMetrics,
    RegimeResult,
    Trade,
)


def test_regime_result_shape() -> None:
    r = RegimeResult(
        symbol="^NSEI",
        method="hmm",
        n_states=3,
        labels=[0, 1, 2],
        state_names={0: "bear", 1: "sideways", 2: "bull"},
        fitted_at=datetime(2026, 1, 1),
    )
    assert r.symbol == "^NSEI"
    assert r.state_names[2] == "bull"


def test_backtest_result_shape() -> None:
    m = PerformanceMetrics(
        cagr=0.1,
        total_return_pct=100.0,
        sharpe=1.0,
        sortino=1.2,
        calmar=0.8,
        information_ratio=0.5,
        max_drawdown_pct=20.0,
        annualized_vol_pct=18.0,
        win_rate_pct=55.0,
        profit_factor=1.5,
        avg_win_pct=2.0,
        avg_loss_pct=1.0,
        num_trades=10,
        exposure_pct=80.0,
        benchmark_return_pct=80.0,
        alpha_pct=5.0,
        beta=1.0,
    )
    b = BacktestResult(
        symbol="RELIANCE.NS",
        strategy="ma_crossover",
        params={"fast": 20, "slow": 50},
        start=date(2020, 1, 1),
        end=date(2025, 1, 1),
        metrics=m,
        equity_curve=[EquityPoint(date=date(2020, 1, 1), equity=100.0, benchmark=100.0)],
        trade_list=[
            Trade(
                entry_date=date(2020, 1, 1),
                exit_date=date(2020, 2, 1),
                direction="long",
                pnl_pct=5.0,
                bars_held=20,
            )
        ],
    )
    assert b.net_of_costs is True
    assert b.metrics.sharpe == 1.0

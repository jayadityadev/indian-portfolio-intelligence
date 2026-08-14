import numpy as np
import pandas as pd
import pytest

from app.backtest.engine import run
from app.backtest.metrics import calculate_metrics


def test_metrics_known_equity_curve() -> None:
    index = pd.date_range("2020-01-01", periods=3, tz="Asia/Kolkata", name="date")
    equity = pd.Series([100.0, 110.0, 121.0], index=index)
    benchmark = pd.Series([100.0, 105.0, 110.0], index=index)
    metrics = calculate_metrics(equity, benchmark, [])
    assert metrics.total_return_pct == pytest.approx(21.0)
    assert metrics.max_drawdown_pct == 0.0
    assert metrics.benchmark_return_pct == pytest.approx(10.0)


def test_all_strategies_return_canonical_result() -> None:
    index = pd.date_range("2020-01-01", periods=300, tz="Asia/Kolkata", name="date")
    close = pd.Series(
        100 * np.exp(np.cumsum(np.random.default_rng(42).normal(0.001, 0.01, 300))),
        index=index,
    )
    features = pd.DataFrame(
        {
            "close": close,
            "returns_pct": close.pct_change(),
            "log_return": np.log(close).diff(),
            "vol_20": close.pct_change().rolling(20).std(),
        },
        index=index,
    )
    for strategy in ("buy_and_hold", "ma_crossover", "rsi", "momentum", "mean_reversion"):
        result = run("TEST.NS", strategy, {}, features)
        assert result.strategy == strategy
        assert result.net_of_costs is True
        assert result.metrics.num_trades == len(result.trade_list)

"""Run the validation layer against the canonical backtest engine.

This module adapts the pure validation primitives (walk-forward, PBO, DSR) to
the existing vectorbt engine, so a worker can produce a TrustReport for a real
symbol/strategy without duplicating the metric math.

It builds a small strategy×params config grid around the requested strategy to
drive the multiple-testing guard (PBO/DSR). All number math flows through
``app.backtest.metrics`` / the validation primitives — nothing ad-hoc.
"""

from __future__ import annotations

import pandas as pd

from app.backtest.engine import run
from app.schemas import StrategyName, TrustReport
from app.validation.service import build_trust_report


def _config_grid(strategy: StrategyName) -> list[dict]:
    """Small parameter grid around the strategy for the multiple-testing guard."""
    if strategy == "ma_crossover":
        return [{"fast": 10, "slow": 30}, {"fast": 20, "slow": 50}, {"fast": 50, "slow": 200}]
    if strategy == "rsi":
        return [
            {"oversold": 30, "overbought": 70},
            {"oversold": 25, "overbought": 75},
            {"oversold": 35, "overbought": 65},
        ]
    if strategy == "momentum":
        return [
            {"lookback": 60},
            {"lookback": 120},
            {"lookback": 200},
        ]
    if strategy == "mean_reversion":
        return [
            {"lookback": 10, "entry_z": -2, "exit_z": 0},
            {"lookback": 20, "entry_z": -2, "exit_z": 0},
            {"lookback": 30, "entry_z": -1.5, "exit_z": 0},
        ]
    return [{}]


def validate_strategy(
    symbol: str,
    strategy: StrategyName,
    features: pd.DataFrame,
    net_of_costs: bool = True,
) -> TrustReport:
    """Run walk-forward + PBO/DSR for one strategy on one symbol."""
    if features.empty or "close" not in features:
        raise ValueError("features must contain a non-empty close series")

    def returns_for(params: dict) -> pd.Series:
        result = run(symbol, strategy, params, features, net_of_costs=net_of_costs)
        equity = pd.Series(
            [p.equity for p in result.equity_curve],
            index=pd.to_datetime([p.date for p in result.equity_curve]),
        )
        return equity.pct_change().dropna()

    full_returns = returns_for({})
    configs = _config_grid(strategy)
    return build_trust_report(
        returns=full_returns,
        runner=returns_for,
        configs=configs,
    )

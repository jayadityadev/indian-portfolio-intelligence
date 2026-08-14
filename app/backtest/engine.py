"""Vectorized backtest execution and canonical result assembly."""

from __future__ import annotations

import pandas as pd
import vectorbt as vbt

from app.backtest.costs import IndianCostModel
from app.backtest.metrics import build_trades, calculate_metrics
from app.backtest.strategies import signals
from app.schemas import BacktestResult, EquityPoint, StrategyName


def run(
    symbol: str,
    strategy: StrategyName,
    params: dict,
    features: pd.DataFrame,
    benchmark: pd.Series | None = None,
    net_of_costs: bool = True,
    costs: IndianCostModel | None = None,
) -> BacktestResult:
    """Run one strategy on one symbol using vectorbt close signals."""
    if features.empty or "close" not in features:
        raise ValueError("features must contain non-empty close series")
    close = features["close"].astype(float).dropna()
    entries, exits = signals(features.reindex(close.index), strategy, params)
    model = costs or IndianCostModel()
    fee = model.per_side_pct if net_of_costs else 0.0
    portfolio = vbt.Portfolio.from_signals(
        close,
        entries=entries.reindex(close.index, fill_value=False),
        exits=exits.reindex(close.index, fill_value=False),
        fees=fee,
        slippage=model.slippage_pct if net_of_costs else 0.0,
        init_cash=100.0,
        freq="1D",
    )
    equity = portfolio.value()
    benchmark = benchmark.reindex(equity.index).ffill() if benchmark is not None else close
    benchmark = benchmark / benchmark.iloc[0] * 100
    trades = build_trades(
        close,
        entries,
        exits,
        net_of_costs=net_of_costs,
        cost_pct=model.round_trip_pct,
    )
    metrics = calculate_metrics(equity, benchmark, trades)
    exposure = float(portfolio.asset_value().gt(0).mean() * 100)
    metrics = metrics.model_copy(update={"exposure_pct": exposure})
    points = [
        EquityPoint(
            date=timestamp.date(),
            equity=float(value),
            benchmark=float(benchmark.loc[timestamp]),
        )
        for timestamp, value in equity.items()
    ]
    return BacktestResult(
        symbol=symbol,
        strategy=strategy,
        params=params,
        start=equity.index[0].date(),
        end=equity.index[-1].date(),
        net_of_costs=net_of_costs,
        metrics=metrics,
        equity_curve=points,
        trade_list=trades,
    )

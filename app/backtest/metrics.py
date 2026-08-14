"""Canonical performance metrics. No other module computes these formulas."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

import numpy as np
import pandas as pd

from app.schemas import PerformanceMetrics, Trade


def calculate_metrics(
    equity: pd.Series,
    benchmark: pd.Series,
    trades: Iterable[Trade] = (),
    risk_free_daily: float = 0.0,
) -> PerformanceMetrics:
    """Calculate every canonical metric from normalized equity and trades."""
    equity = equity.astype(float).dropna()
    benchmark = benchmark.reindex(equity.index).astype(float).ffill().dropna()
    if len(equity) < 2:
        raise ValueError("at least two equity observations are required")
    returns = equity.pct_change().dropna()
    benchmark_returns = benchmark.pct_change().reindex(returns.index).dropna()
    years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1 / 365.25)
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1
    annualized_vol = returns.std(ddof=1) * np.sqrt(252)
    excess = returns - risk_free_daily
    sharpe = _safe_ratio(excess.mean() * np.sqrt(252), returns.std(ddof=1))
    downside = excess.where(excess < 0, 0.0)
    sortino = _safe_ratio(excess.mean() * np.sqrt(252), downside.std(ddof=1))
    drawdown = equity / equity.cummax() - 1
    max_drawdown = float(drawdown.min())
    calmar = _safe_ratio(cagr, abs(max_drawdown))
    active = returns.reindex(benchmark_returns.index) - benchmark_returns
    information_ratio = _safe_ratio(active.mean() * np.sqrt(252), active.std(ddof=1))
    beta = _safe_ratio(
        float(returns.reindex(benchmark_returns.index).cov(benchmark_returns)),
        float(benchmark_returns.var(ddof=1)),
    )
    alpha = (returns.mean() - beta * benchmark_returns.mean()) * 252
    trade_list = list(trades)
    wins = [trade.pnl_pct for trade in trade_list if trade.pnl_pct > 0]
    losses = [trade.pnl_pct for trade in trade_list if trade.pnl_pct < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    return PerformanceMetrics(
        cagr=float(cagr),
        total_return_pct=float(total_return * 100),
        sharpe=float(sharpe),
        sortino=float(sortino),
        calmar=float(calmar),
        information_ratio=float(information_ratio),
        max_drawdown_pct=float(abs(max_drawdown) * 100),
        annualized_vol_pct=float(annualized_vol * 100),
        win_rate_pct=float(len(wins) / len(trade_list) * 100) if trade_list else 0.0,
        profit_factor=float(gross_profit / gross_loss) if gross_loss else 0.0,
        avg_win_pct=float(np.mean(wins)) if wins else 0.0,
        avg_loss_pct=float(abs(np.mean(losses))) if losses else 0.0,
        num_trades=len(trade_list),
        exposure_pct=0.0,
        benchmark_return_pct=float((benchmark.iloc[-1] / benchmark.iloc[0] - 1) * 100),
        alpha_pct=float(alpha * 100),
        beta=float(beta),
    )


def _safe_ratio(numerator: float, denominator: float) -> float:
    if not np.isfinite(denominator) or abs(denominator) < 1e-12:
        return 0.0
    return float(numerator / denominator)


def build_trades(
    close: pd.Series,
    entries: pd.Series,
    exits: pd.Series,
    net_of_costs: bool = True,
    cost_pct: float = 0.003,
) -> list[Trade]:
    """Turn boolean entry/exit signals into canonical long trades."""
    trades: list[Trade] = []
    entry_date: date | None = None
    entry_price = 0.0
    for timestamp, price in close.items():
        if entry_date is None and bool(entries.get(timestamp, False)):
            entry_date = timestamp.date()
            entry_price = float(price)
        elif entry_date is not None and bool(exits.get(timestamp, False)):
            pnl = (float(price) / entry_price - 1) * 100
            if net_of_costs:
                pnl -= cost_pct * 100
            trades.append(
                Trade(
                    entry_date=entry_date,
                    exit_date=timestamp.date(),
                    direction="long",
                    pnl_pct=pnl,
                    bars_held=max((timestamp.date() - entry_date).days, 0),
                )
            )
            entry_date = None
    if entry_date is not None and len(close):
        timestamp = close.index[-1]
        pnl = (float(close.iloc[-1]) / entry_price - 1) * 100
        if net_of_costs:
            pnl -= cost_pct * 100
        trades.append(
            Trade(
                entry_date=entry_date,
                exit_date=timestamp.date(),
                direction="long",
                pnl_pct=pnl,
                bars_held=max((timestamp.date() - entry_date).days, 0),
            )
        )
    return trades

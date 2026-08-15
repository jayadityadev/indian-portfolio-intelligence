"""Plotly chart builders for API delivery.

Builders return Plotly JSON. They do not calculate trading metrics or fetch data.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.schemas import BacktestResult, CompareReport, Recommendation, RegimeResult

MAX_POINTS = 2000


def price_with_regime(records: Sequence[Mapping[str, Any]], regime: RegimeResult) -> str:
    rows = _sample(records)
    figure = go.Figure()
    if not rows:
        return _json(figure)
    dates = [row.get("date") for row in rows]
    figure.add_trace(
        go.Scatter(
            x=dates,
            y=[row.get("close") for row in rows],
            mode="lines",
            name="Close",
        )
    )
    labels = regime.labels[: len(rows)]
    for start, end, state in _runs(labels):
        if start >= len(dates):
            continue
        figure.add_vrect(
            x0=dates[start],
            x1=dates[min(end, len(dates) - 1)],
            fillcolor=_REGIME_COLORS.get(regime.state_names.get(state, ""), "gray"),
            opacity=0.12,
            line_width=0,
        )
    figure.update_layout(title="Price and market regime", xaxis_title="Date", yaxis_title="Price")
    return _json(figure)


def equity_vs_benchmark(result: BacktestResult) -> str:
    points = _sample(result.equity_curve)
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(x=[p.date for p in points], y=[p.equity for p in points], name="Strategy")
    )
    figure.add_trace(
        go.Scatter(x=[p.date for p in points], y=[p.benchmark for p in points], name="Benchmark")
    )
    figure.update_layout(title=f"{result.strategy}: equity vs benchmark", yaxis_title="Equity")
    return _json(figure)


def drawdown(result: BacktestResult) -> str:
    points = _sample(result.equity_curve)
    equity = np.asarray([point.equity for point in points], dtype=float)
    drawdowns = equity / np.maximum.accumulate(equity) - 1 if len(equity) else equity
    figure = go.Figure(go.Scatter(x=[p.date for p in points], y=drawdowns * 100, name="Drawdown"))
    figure.update_layout(title="Drawdown", yaxis_title="Drawdown (%)")
    return _json(figure)


def strategy_comparison(report: CompareReport) -> str:
    strategies = [result.strategy for result in report.results]
    metrics = {
        "CAGR (%)": [result.metrics.cagr * 100 for result in report.results],
        "Sharpe": [result.metrics.sharpe for result in report.results],
        "Max DD (%)": [-result.metrics.max_drawdown_pct for result in report.results],
    }
    figure = make_subplots(rows=1, cols=len(metrics), subplot_titles=list(metrics))
    for column, (metric, values) in enumerate(metrics.items(), start=1):
        figure.add_trace(
            go.Bar(x=strategies, y=values, name=metric, showlegend=False), row=1, col=column
        )
    figure.update_layout(title="Strategy comparison")
    return _json(figure)


def suitability_bars(recommendation: Recommendation | Mapping[str, float]) -> str:
    values = (
        recommendation.suitability
        if isinstance(recommendation, Recommendation)
        else dict(recommendation)
    )
    figure = go.Figure(go.Bar(x=list(values), y=list(values.values()), name="Suitability"))
    figure.update_layout(title="Strategy suitability", yaxis_title="Score", yaxis_range=[0, 1])
    return _json(figure)


def trade_scatter(result: BacktestResult) -> str:
    trades = result.trade_list
    figure = go.Figure(
        go.Scatter(
            x=[trade.exit_date for trade in trades],
            y=[trade.pnl_pct for trade in trades],
            mode="markers",
            marker_color=["green" if trade.pnl_pct >= 0 else "red" for trade in trades],
            name="Trade P&L",
        )
    )
    figure.update_layout(title="Trade outcomes", yaxis_title="P&L (%)")
    return _json(figure)


_REGIME_COLORS = {"bull": "green", "bear": "red", "sideways": "orange"}


def _sample(values: Sequence[Any]) -> list[Any]:
    if len(values) <= MAX_POINTS:
        return list(values)
    indexes = np.linspace(0, len(values) - 1, MAX_POINTS, dtype=int)
    return [values[index] for index in indexes]


def _runs(labels: Sequence[int]) -> list[tuple[int, int, int]]:
    if not labels:
        return []
    runs: list[tuple[int, int, int]] = []
    start = 0
    current = labels[0]
    for index, label in enumerate(labels[1:], start=1):
        if label != current:
            runs.append((start, index - 1, current))
            start, current = index, label
    runs.append((start, len(labels) - 1, current))
    return runs


def _json(figure: go.Figure) -> str:
    return cast(str, figure.to_json())

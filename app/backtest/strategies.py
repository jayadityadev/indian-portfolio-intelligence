"""Canonical strategy signal definitions."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from app.schemas import StrategyName

SignalPair = tuple[pd.Series, pd.Series]


def signals(
    features: pd.DataFrame, strategy: StrategyName, params: dict | None = None
) -> SignalPair:
    """Return close-evaluated entry and exit signals without lookahead."""
    params = params or {}
    close = features["close"]
    if strategy == "buy_and_hold":
        entries = pd.Series(False, index=features.index)
        exits = pd.Series(False, index=features.index)
        if len(features):
            entries.iloc[0] = True
            exits.iloc[-1] = True
        return entries, exits
    if strategy == "ma_crossover":
        fast = int(params.get("fast", 20))
        slow = int(params.get("slow", 50))
        fast_ma = features.get(f"sma_{fast}", close.rolling(fast).mean())
        slow_ma = features.get(f"sma_{slow}", close.rolling(slow).mean())
        return _crosses_above(fast_ma, slow_ma), _crosses_below(fast_ma, slow_ma)
    if strategy == "rsi":
        rsi = features.get("rsi_14", _rsi(close, int(params.get("n", 14))))
        return rsi < float(params.get("oversold", 30)), rsi > float(params.get("overbought", 70))
    if strategy == "momentum":
        lookback = int(params.get("lookback", 120))
        momentum = features.get("momentum_60", close.pct_change(lookback))
        sma = features.get("sma_200", close.rolling(200).mean())
        entries = (momentum > 0) & (close > sma)
        exits = (momentum < 0) | (close < sma)
        return entries & ~entries.shift(1, fill_value=False), exits
    if strategy == "mean_reversion":
        lookback = int(params.get("lookback", 20))
        zscore = (close - close.rolling(lookback).mean()) / close.rolling(lookback).std()
        return zscore < float(params.get("entry_z", -2)), zscore > float(params.get("exit_z", 0))
    raise ValueError(f"unsupported strategy: {strategy}")


STRATEGY_REGISTRY: dict[str, Callable[..., SignalPair]] = {
    name: signals for name in ("buy_and_hold", "ma_crossover", "rsi", "momentum", "mean_reversion")
}


def _crosses_above(left: pd.Series, right: pd.Series) -> pd.Series:
    return (left > right) & (left.shift(1) <= right.shift(1))


def _crosses_below(left: pd.Series, right: pd.Series) -> pd.Series:
    return (left < right) & (left.shift(1) >= right.shift(1))


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    losses = -delta.clip(upper=0).ewm(alpha=1 / period, adjust=False).mean()
    return 100 - 100 / (1 + gains / losses.replace(0, float("nan")))

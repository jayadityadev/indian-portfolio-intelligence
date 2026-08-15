"""Raw-vs-adjusted integrity validation.

Owner: Jayaditya (interface) / Chirag (validate-data script uses this).

Purpose: an unadjusted series silently corrupts every downstream backtest. This
module compares raw (``auto_adjust=False``) vs adjusted prices and flags split /
bonus events where the ratio must jump exactly at the ex-date.

Contract:
    validate_adjustment(symbol) -> AdjustmentReport
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import yfinance as yf
from pydantic import BaseModel


class AdjustmentReport(BaseModel):
    symbol: str
    ok: bool
    detected_events: int
    note: str | None = None


def validate_adjustment(symbol: str) -> AdjustmentReport:
    end = date.today()
    start = end - timedelta(days=365 * 20)
    raw = yf.download(
        symbol, start=start, end=end, auto_adjust=False, progress=False, threads=False
    )
    adjusted = yf.download(
        symbol, start=start, end=end, auto_adjust=True, progress=False, threads=False
    )
    if raw.empty or adjusted.empty:
        return AdjustmentReport(symbol=symbol, ok=False, detected_events=0, note="no data")
    raw_close = _close(raw)
    adjusted_close = _close(adjusted)
    joined = pd.concat([raw_close, adjusted_close], axis=1, join="inner").dropna()
    joined.columns = ["raw", "adjusted"]
    ratio = joined["raw"] / joined["adjusted"]
    jumps = ratio.pct_change().abs().dropna()
    events = int((jumps > 0.01).sum())
    ok = bool((ratio > 0).all() and np.isfinite(ratio).all())
    note = None if ok else "invalid raw/adjusted price ratio"
    return AdjustmentReport(symbol=symbol, ok=ok, detected_events=events, note=note)


def _close(frame: pd.DataFrame) -> pd.Series:
    if isinstance(frame.columns, pd.MultiIndex):
        frame = frame.xs(frame.columns.get_level_values(1)[0], axis=1, level=1)
    return frame["Close"]

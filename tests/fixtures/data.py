"""Deterministic synthetic OHLCV fixtures."""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_ohlcv(rows: int = 320) -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=rows, freq="B", name="date", tz="Asia/Kolkata")
    close = pd.Series(np.linspace(100, 180, rows), index=index)
    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 100_000.0,
        },
        index=index,
    )

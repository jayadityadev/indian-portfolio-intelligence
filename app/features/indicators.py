"""Pure OHLCV feature engineering.

Rolling indicators intentionally preserve leading NaNs. Filling those values
would manufacture information before enough history exists.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import AverageTrueRange

from app.schemas import FEATURE_COLUMNS, OHLCV_COLUMNS

EWMA_LAMBDA = 0.94


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    """Return OHLCV data plus canonical feature columns, without I/O."""
    missing = [column for column in OHLCV_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"OHLCV frame missing columns: {missing}")
    result = frame.copy()
    close = result["close"].astype(float)
    returns = close.pct_change()
    result["returns_pct"] = returns
    result["log_return"] = np.log(close).diff()
    result["vol_20"] = returns.rolling(20).std()
    result["vol_ewma"] = ewma_volatility(returns)
    result["sma_20"] = close.rolling(20).mean()
    result["sma_50"] = close.rolling(50).mean()
    result["sma_200"] = close.rolling(200).mean()
    result["ema_12"] = close.ewm(span=12, adjust=False, min_periods=12).mean()
    result["ema_26"] = close.ewm(span=26, adjust=False, min_periods=26).mean()

    result["rsi_14"] = RSIIndicator(close=close, window=14, fillna=False).rsi()
    macd = MACD(close=close, window_slow=26, window_fast=12, window_sign=9, fillna=False)
    result["macd"] = macd.macd()
    result["macd_signal"] = macd.macd_signal()
    result["momentum_20"] = close.pct_change(20)
    result["momentum_60"] = close.pct_change(60)
    result["atr_14"] = AverageTrueRange(
        high=result["high"].astype(float),
        low=result["low"].astype(float),
        close=close,
        window=14,
        fillna=False,
    ).average_true_range()
    result["max_drawdown_rolling"] = close / close.rolling(252).max() - 1
    return result.loc[:, [*OHLCV_COLUMNS, *FEATURE_COLUMNS]]


def ewma_volatility(returns: pd.Series, lambda_: float = EWMA_LAMBDA) -> pd.Series:
    """RiskMetrics EWMA volatility from decimal daily returns.

    Variance follows ``lambda * previous_variance + (1-lambda) * r²``.
    """
    if not 0 < lambda_ < 1:
        raise ValueError("lambda_ must be between 0 and 1")
    clean = returns.astype(float)
    variance = clean.pow(2).ewm(alpha=1 - lambda_, adjust=False).mean()
    return np.sqrt(variance)

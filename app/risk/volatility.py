"""Volatility estimators."""

from __future__ import annotations

import pandas as pd

from app.features.indicators import EWMA_LAMBDA, ewma_volatility


def annualized_ewma_volatility(
    returns: pd.Series,
    lambda_: float = EWMA_LAMBDA,
    periods_per_year: int = 252,
) -> float:
    """Return latest EWMA daily volatility annualized as a decimal."""
    if returns.dropna().empty:
        return 0.0
    return float(ewma_volatility(returns, lambda_).iloc[-1] * periods_per_year**0.5)

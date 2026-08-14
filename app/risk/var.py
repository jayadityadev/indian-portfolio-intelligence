"""Historical and parametric one-day tail-risk estimators."""

from __future__ import annotations

import pandas as pd
from scipy.stats import norm


def historical_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """Return historical VaR as positive loss fraction."""
    _validate_confidence(confidence)
    clean = returns.dropna().astype(float)
    return max(float(-clean.quantile(1 - confidence)), 0.0) if len(clean) else 0.0


def expected_shortfall(returns: pd.Series, confidence: float = 0.95) -> float:
    """Return mean loss beyond historical VaR as positive fraction."""
    _validate_confidence(confidence)
    clean = returns.dropna().astype(float)
    if clean.empty:
        return 0.0
    cutoff = clean.quantile(1 - confidence)
    tail = clean[clean <= cutoff]
    return max(float(-tail.mean()), 0.0) if not tail.empty else 0.0


def parametric_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """Return normal-parametric VaR as positive loss fraction."""
    _validate_confidence(confidence)
    clean = returns.dropna().astype(float)
    if clean.empty:
        return 0.0
    z = norm.ppf(1 - confidence)
    return max(float(-(clean.mean() + z * clean.std(ddof=1))), 0.0)


def max_drawdown_pct(close: pd.Series) -> float:
    """Return maximum peak-to-trough decline as positive percentage."""
    clean = close.dropna().astype(float)
    if clean.empty:
        return 0.0
    drawdown = clean / clean.cummax() - 1
    return max(float(-drawdown.min() * 100), 0.0)


def _validate_confidence(confidence: float) -> None:
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")

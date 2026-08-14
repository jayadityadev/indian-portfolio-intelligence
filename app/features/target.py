"""Leak-free target builders for forward-looking models."""

from __future__ import annotations

import numpy as np
import pandas as pd


def forward_return_bins(
    close: pd.Series,
    horizon: int = 5,
    n_bins: int = 3,
) -> pd.Series:
    """Label each timestamp by its future return quantile.

    ``shift(-horizon)`` makes target at ``t`` depend on future prices while all
    features at ``t`` remain causal. Last ``horizon`` rows are NaN.
    """
    if horizon < 1 or n_bins < 2:
        raise ValueError("horizon must be positive and n_bins must be at least two")
    future_return = close.shift(-horizon) / close - 1
    valid = future_return.dropna()
    if valid.nunique() < n_bins:
        return pd.Series(np.nan, index=close.index, dtype=float, name="forward_return_bin")
    labels = pd.qcut(valid, q=n_bins, labels=False, duplicates="drop")
    result = pd.Series(np.nan, index=close.index, name="forward_return_bin")
    result.loc[labels.index] = labels.astype(float)
    return result


def regime_label_windows(
    close: pd.Series,
    horizon: int = 20,
    bull_threshold: float = 0.05,
    bear_threshold: float = -0.05,
) -> pd.Series:
    """Create future-window bear/sideways/bull labels without lookahead leakage.

    Labels are integer-coded ``0=bear, 1=sideways, 2=bull`` and describe the
    return from ``t`` to ``t+horizon``. Final horizon rows are NaN.
    """
    if horizon < 1 or bear_threshold >= bull_threshold:
        raise ValueError("invalid horizon or regime thresholds")
    future_return = close.shift(-horizon) / close - 1
    labels = pd.Series(np.nan, index=close.index, name="regime_label")
    labels.loc[future_return <= bear_threshold] = 0
    labels.loc[future_return >= bull_threshold] = 2
    middle = future_return.notna() & future_return.between(
        bear_threshold, bull_threshold, inclusive="neither"
    )
    labels.loc[middle] = 1
    return labels

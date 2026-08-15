"""Gaussian HMM market-regime detector."""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

from app.regime.baselines import fit_kmeans
from app.schemas import RegimeMethod, RegimeResult


def fit_hmm(features: pd.DataFrame, symbol: str = "unknown", n_states: int = 3) -> RegimeResult:
    """Fit causal-compatible HMM input and normalize state IDs by mean return.

    Falls back to k-means if HMM covariance estimation fails (common with short
    or near-collinear series).
    """
    if n_states < 2:
        raise ValueError("n_states must be at least two")
    columns = [column for column in ("log_return", "vol_20") if column in features]
    if not columns:
        raise ValueError("features need log_return or returns_pct")
    if "log_return" not in columns and "returns_pct" in features:
        columns = ["returns_pct", *[column for column in columns if column != "returns_pct"]]
    clean = features.loc[:, columns].replace([np.inf, -np.inf], np.nan).dropna()
    if len(clean) < n_states * 5:
        raise ValueError("not enough clean observations to fit HMM")

    try:
        model = GaussianHMM(
            n_components=n_states,
            covariance_type="diag",
            n_iter=50,
            tol=0.01,
            random_state=42,
        )
        model.fit(clean.to_numpy())
        raw_labels = model.predict(clean.to_numpy())
        log_likelihood = float(model.score(clean.to_numpy()))
        method: RegimeMethod = "hmm"
    except (ValueError, np.linalg.LinAlgError):
        raw_labels = fit_kmeans(features, n_states=n_states)
        clean = clean.loc[clean.index.isin(features.index)]
        raw_labels = raw_labels[: len(clean)]
        log_likelihood = None
        method = "kmeans"

    returns = (
        features.loc[clean.index, "returns_pct"] if "returns_pct" in features else clean.iloc[:, 0]
    )
    means = pd.Series(returns.to_numpy()).groupby(raw_labels).mean()
    ordered = list(means.sort_values().index)
    remap = {old: new for new, old in enumerate(ordered)}
    labels = pd.Series(raw_labels, index=clean.index).map(remap)
    labels = _smooth_labels(labels, window=20)
    state_names = {state: name for state, name in enumerate(_state_names(n_states))}
    full_labels = pd.Series(index=features.index, dtype="Int64")
    full_labels.loc[labels.index] = labels.astype(int)
    return RegimeResult(
        symbol=symbol,
        method=method,
        n_states=n_states,
        labels=full_labels.dropna().astype(int).tolist(),
        state_names=state_names,
        log_likelihood=log_likelihood,
        fitted_at=datetime.now(),
    )


def _state_names(n_states: int) -> list[str]:
    if n_states == 3:
        return ["bear", "sideways", "bull"]
    return [f"state_{index}" for index in range(n_states)]


def _smooth_labels(labels: pd.Series, window: int = 20) -> pd.Series:
    """Apply a rolling-mode filter so regimes persist for multi-week stretches."""
    if len(labels) < window:
        return labels

    def _mode(arr: np.ndarray) -> int:
        values, counts = np.unique(arr, return_counts=True)
        return int(values[np.argmax(counts)])

    return labels.rolling(window, center=True, min_periods=1).apply(_mode).astype(int)

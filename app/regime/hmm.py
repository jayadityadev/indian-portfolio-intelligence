"""Gaussian HMM market-regime detector."""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

from app.schemas import RegimeResult


def fit_hmm(features: pd.DataFrame, symbol: str = "unknown", n_states: int = 3) -> RegimeResult:
    """Fit causal-compatible HMM input and normalize state IDs by mean return."""
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
    model = GaussianHMM(
        n_components=n_states,
        covariance_type="full",
        n_iter=200,
        random_state=42,
    )
    model.fit(clean.to_numpy())
    raw_labels = model.predict(clean.to_numpy())
    returns = (
        features.loc[clean.index, "returns_pct"] if "returns_pct" in features else clean.iloc[:, 0]
    )
    means = pd.Series(returns.to_numpy()).groupby(raw_labels).mean()
    ordered = list(means.sort_values().index)
    remap = {old: new for new, old in enumerate(ordered)}
    labels = pd.Series(raw_labels, index=clean.index).map(remap)
    state_names = {state: name for state, name in enumerate(_state_names(n_states))}
    full_labels = pd.Series(index=features.index, dtype="Int64")
    full_labels.loc[labels.index] = labels.astype(int)
    return RegimeResult(
        symbol=symbol,
        method="hmm",
        n_states=n_states,
        labels=full_labels.dropna().astype(int).tolist(),
        state_names=state_names,
        log_likelihood=float(model.score(clean.to_numpy())),
        fitted_at=datetime.now(),
    )


def _state_names(n_states: int) -> list[str]:
    if n_states == 3:
        return ["bear", "sideways", "bull"]
    return [f"state_{index}" for index in range(n_states)]

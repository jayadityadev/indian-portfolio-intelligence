"""Unsupervised regime baselines."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans


def fit_kmeans(features: pd.DataFrame, n_states: int = 3) -> np.ndarray:
    """Cluster feature observations with ordinary Euclidean k-means."""
    clean = _clean(features)
    model = KMeans(n_clusters=n_states, n_init=20, random_state=42)
    labels = model.fit_predict(clean.to_numpy())
    return _ordered_labels(labels, clean)


def fit_wasserstein_kmeans(features: pd.DataFrame, n_states: int = 3) -> np.ndarray:
    """Approximate Wasserstein k-means using rolling return-distribution features.

    In one dimension, Wasserstein distance is the squared distance between
    quantile functions. Quantile summaries make this baseline deterministic and
    avoid treating a whole rolling distribution as a single point estimate.
    """
    clean = _clean(features)
    values = clean.iloc[:, 0].to_numpy()
    windows = np.array(
        [np.quantile(values[max(0, i - 19) : i + 1], [0.1, 0.5, 0.9]) for i in range(len(values))]
    )
    labels = KMeans(n_clusters=n_states, n_init=20, random_state=42).fit_predict(windows)
    return _ordered_labels(labels, clean)


def _clean(features: pd.DataFrame) -> pd.DataFrame:
    columns = [column for column in ("log_return", "vol_20") if column in features]
    if not columns:
        columns = ["returns_pct"]
    return features.loc[:, columns].replace([np.inf, -np.inf], np.nan).dropna()


def _ordered_labels(labels: np.ndarray, features: pd.DataFrame) -> np.ndarray:
    returns = features.iloc[:, 0]
    means = pd.Series(returns.to_numpy()).groupby(labels).mean().sort_values()
    remap = {old: new for new, old in enumerate(means.index)}
    return np.array([remap[label] for label in labels], dtype=int)

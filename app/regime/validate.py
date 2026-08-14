"""Clustering validation metrics used to compare regime methods."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import davies_bouldin_score

from app.schemas import RegimeValidation


def validate_regimes(
    features: pd.DataFrame,
    labels: np.ndarray | list[int],
    baseline_labels: np.ndarray | list[int] | None = None,
) -> RegimeValidation:
    clean = _clean(features)
    labels_array = np.asarray(labels, dtype=int)[-len(clean) :]
    data = clean.to_numpy()
    db = float(davies_bouldin_score(data, labels_array))
    dunn = dunn_index(data, labels_array)
    mmd = maximum_mean_discrepancy(data, labels_array, baseline_labels)
    transitions = transition_matrix(labels_array)
    return RegimeValidation(
        davies_bouldin=db,
        dunn_index=dunn,
        mmd=mmd,
        transition_matrix=transitions,
    )


def dunn_index(data: np.ndarray, labels: np.ndarray) -> float:
    clusters = [data[labels == label] for label in np.unique(labels)]
    if len(clusters) < 2:
        return 0.0
    max_intra = max(_pairwise_distances(cluster).max(initial=0.0) for cluster in clusters)
    min_inter = min(
        _pairwise_distances_between(left, right).min(initial=float("inf"))
        for index, left in enumerate(clusters)
        for right in clusters[index + 1 :]
    )
    return float(min_inter / max_intra) if max_intra else 0.0


def maximum_mean_discrepancy(
    data: np.ndarray,
    labels: np.ndarray,
    baseline_labels: np.ndarray | list[int] | None,
) -> float:
    if baseline_labels is None:
        return 0.0
    baseline = np.asarray(baseline_labels, dtype=int)[-len(data) :]
    means = [data[labels == label].mean(axis=0) for label in np.unique(labels)]
    baseline_means = [data[baseline == label].mean(axis=0) for label in np.unique(baseline)]
    return float(min(np.linalg.norm(left - right) for left in means for right in baseline_means))


def transition_matrix(labels: np.ndarray) -> list[list[float]]:
    states = sorted(np.unique(labels))
    matrix = np.zeros((len(states), len(states)))
    for previous, current in zip(labels[:-1], labels[1:], strict=True):
        matrix[previous, current] += 1
    row_sums = matrix.sum(axis=1, keepdims=True)
    matrix = np.divide(matrix, row_sums, out=np.zeros_like(matrix), where=row_sums != 0)
    return list(matrix.tolist())


def _clean(features: pd.DataFrame) -> pd.DataFrame:
    columns = [column for column in ("log_return", "vol_20") if column in features]
    if not columns:
        columns = ["returns_pct"]
    return features.loc[:, columns].replace([np.inf, -np.inf], np.nan).dropna()


def _pairwise_distances(data: np.ndarray) -> np.ndarray:
    return _pairwise_distances_between(data, data)


def _pairwise_distances_between(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    return np.asarray(np.linalg.norm(left[:, None, :] - right[None, :, :], axis=2))

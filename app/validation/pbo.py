"""Probability of Backtest Overfitting (PBO) via Combinatorially Symmetric CV.

PBO is the probability that a configuration selected as optimal in-sample
underperforms the median out-of-sample (paper #12 §2.5.1, Bailey et al. 2016).

Given a performance matrix M of shape (T observations × N configurations) of
per-config returns:

  1. Split M into S disjoint submatrices (ordered along time).
  2. For each of the C(S, S/2) in-sample/out-of-sample combinations:
       a. pick the config with the best in-sample log-return ratio,
       b. rank that config among all configs on the out-of-sample submatrix,
       c. map the rank to a logit lambda.
  3. PBO = fraction of combinations where the IS-best config ranks below the
     OOS median (lambda < 0), i.e. P(lambda < 0).

The module is pure (NumPy only) and unit-testable with synthetic matrices.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np


def _logit(rank: int, n_configs: int) -> float:
    """Map a config's OOS rank to a logit; rank is 1-based (1 = best)."""
    if n_configs <= 1:
        return 0.0
    frac = rank / (n_configs + 1)
    return float(np.log(frac / (1 - frac)))


def cscv_pbo(matrix: np.ndarray, n_splits: int = 8) -> float:
    """Compute PBO from a T×N matrix of per-config returns via CSCV.

    Parameters
    ----------
    matrix:
        Shape (T, N). Each column is one configuration's returns over T rows.
    n_splits:
        Number S of disjoint time submatrices. Must be even and ≤ T.

    Returns
    -------
    PBO in [0, 1].
    """
    matrix = np.asarray(matrix, dtype=float)
    t, n_configs = matrix.shape
    if n_splits % 2 != 0:
        raise ValueError("n_splits must be even for CSCV pairing")
    if n_splits > t:
        raise ValueError("n_splits cannot exceed observation rows")
    if n_configs < 2:
        return 0.0

    n_groups = min(n_splits, t)
    bounds = np.linspace(0, t, n_groups + 1).astype(int)
    submatrices = [matrix[bounds[i] : bounds[i + 1]] for i in range(n_groups)]
    half = n_groups // 2
    lambdas: list[float] = []

    for combo in combinations(range(n_groups), half):
        in_groups = set(combo)
        in_idx = np.array([g for g in range(n_groups) if g in in_groups])
        out_idx = np.array([g for g in range(n_groups) if g not in in_groups])
        in_mat = np.vstack([submatrices[i] for i in in_idx])
        out_mat = np.vstack([submatrices[i] for i in out_idx])
        if in_mat.size == 0 or out_mat.size == 0:
            continue

        in_score = in_mat.sum(axis=0)  # cumulative log-return per config
        best_config = int(np.argmax(in_score))
        out_score = out_mat.sum(axis=0)
        # rank of the IS-best config among OOS configs (1 = highest OOS return)
        rank = int((out_score > out_score[best_config]).sum()) + 1
        lambdas.append(_logit(rank, n_configs))

    if not lambdas:
        return 0.0
    return float(np.mean(np.array(lambdas) < 0.0))

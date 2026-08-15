"""Walk-forward out-of-sample evaluation for rule-based strategies.

For rule-based strategies there is no trainable model, so "walk-forward" here
means evaluating the strategy's performance on successive, time-ordered
out-of-sample windows to demonstrate consistency and avoid in-sample cherry
picking (plan §14.3). Each fold yields OOS returns; the caller aggregates them
into a TrustReport.

The splitter is deliberately kept pure (no I/O) so it is unit-testable against
synthetic features and reusable by the CPCV module.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class WalkForwardSplit:
    """One expanding-window fold.

    ``train_slice`` and ``test_slice`` are row indices (integer positions) into
    the source frame, so the splitter stays pandas-free and leak-free.
    """

    train_slice: slice
    test_slice: slice


def expanding_windows(
    n_obs: int,
    n_folds: int,
    min_train: int = 252,
    gap: int = 0,
) -> list[WalkForwardSplit]:
    """Build expanding-window train/test slices in time order.

    Parameters
    ----------
    n_obs:
        Total number of observations (rows).
    n_folds:
        Number of out-of-sample folds.
    min_train:
        Minimum training rows in the first fold.
    gap:
        Optional embargo gap between train and test (rows).

    Returns
    -------
    Folds ordered oldest → newest; each test window strictly follows its
    training window plus ``gap`` rows.
    """
    if n_obs < min_train + n_folds:
        raise ValueError(
            f"not enough observations ({n_obs}) for {n_folds} folds with min_train={min_train}"
        )
    span = n_obs - min_train
    test_size = max(span // n_folds, 1)
    folds: list[WalkForwardSplit] = []
    start = min_train
    for _ in range(n_folds):
        if start + gap >= n_obs:
            break
        end = min(start + test_size, n_obs)
        train_start = 0 if not folds else folds[-1].train_slice.start
        folds.append(
            WalkForwardSplit(
                train_slice=slice(train_start, start),
                test_slice=slice(start + gap, end),
            )
        )
        start = end
    if not folds:
        raise ValueError("no folds produced; increase n_obs or reduce n_folds")
    return folds


def oos_returns(
    returns: pd.Series,
    folds: list[WalkForwardSplit],
) -> list[pd.Series]:
    """Return the out-of-sample returns for each fold."""
    out: list[pd.Series] = []
    for fold in folds:
        idx = np.arange(len(returns))[fold.test_slice]
        out.append(returns.iloc[idx])
    return out

"""Combinatorial Purged Cross-Validation (CPCV) splitter (paper #12 §2.4.4).

CPCV partitions the T observations into N ordered groups, chooses k groups for
testing across all combinations, and applies **purge** (drop train samples whose
label window overlaps the test window) plus an **embargo** gap (drop a further
band of train samples adjacent to the test window).

The purge/embargo sizes are expressed in *rows* and are enforced as an
invariant: any pair of train/test samples must be separated by ≥ embargo rows.
A dedicated helper (``assert_embargo``) lets tests assert the gap, satisfying
plan §14.4.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np


@dataclass(frozen=True)
class CpcvFold:
    """One CPCV combination: training group indices and test group indices."""

    train_groups: tuple[int, ...]
    test_groups: tuple[int, ...]


def combinatorial_splits(
    n_obs: int,
    n_groups: int,
    n_test_groups: int,
) -> list[CpcvFold]:
    """Generate all C(n_groups, n_test_groups) train/test group combinations.

    Training is the complement of the chosen test groups (López de Prado's CPCV
    trains on every configuration in which a group is *not* in the test set).
    """
    folds: list[CpcvFold] = []
    for test_groups in combinations(range(n_groups), n_test_groups):
        test = set(test_groups)
        train = tuple(g for g in range(n_groups) if g not in test)
        folds.append(CpcvFold(train_groups=train, test_groups=test_groups))
    return folds


def purge_embargo_train_mask(
    n_obs: int,
    test_bounds: list[tuple[int, int]],
    embargo: int,
    purge_before: int = 0,
) -> np.ndarray:
    """Boolean mask of train rows that do NOT leak into the test groups.

    Parameters
    ----------
    test_bounds:
        (start, end) row bounds of the test set (merged across test groups).
    embargo:
        Number of rows to drop after the test window as a buffer.
    purge_before:
        Number of rows to drop before the test window (label lookback overlap).

    Returns
    -------
    A boolean array of length ``n_obs``; True = usable as training data.
    """
    mask = np.ones(n_obs, dtype=bool)
    for t_start, t_end in test_bounds:
        lo = max(t_start - purge_before, 0)
        hi = min(t_end + embargo, n_obs)
        mask[lo:hi] = False
    return mask


def assert_embargo(
    train_indices: np.ndarray,
    test_indices: np.ndarray,
    embargo: int,
) -> None:
    """Assert every train/test pair is separated by ≥ ``embargo`` rows.

    Raises ``ValueError`` on violation so leakage cannot silently slip through.
    """
    if train_indices.size == 0 or test_indices.size == 0:
        return
    train = train_indices.reshape(-1, 1)
    test = test_indices.reshape(1, -1)
    gaps = train - test
    close = (gaps > -embargo) & (gaps < embargo)
    if bool(close.any()):
        raise ValueError(f"embargo violated: found train/test rows closer than {embargo} rows")

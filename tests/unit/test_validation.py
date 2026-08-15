"""Unit tests for the validation layer (V1)."""

import numpy as np
import pandas as pd
import pytest

from app.validation.cpcv import (
    assert_embargo,
    combinatorial_splits,
    purge_embargo_train_mask,
)
from app.validation.dsr import dsr, expected_max_sharpe, psr
from app.validation.pbo import cscv_pbo
from app.validation.service import build_trust_report
from app.validation.walk_forward import expanding_windows


def test_expanding_windows_are_ordered_and_disjoint() -> None:
    folds = expanding_windows(n_obs=1000, n_folds=5, min_train=300, gap=0)
    assert len(folds) >= 1
    for fold in folds:
        assert fold.train_slice.stop <= fold.test_slice.start


def test_embargo_assertion_passes_for_separated_folds() -> None:
    n_obs = 1000
    embargo = 200
    folds = expanding_windows(n_obs, n_folds=3, min_train=300, gap=embargo)
    for fold in folds:
        train_idx = np.arange(n_obs)[fold.train_slice]
        test_idx = np.arange(n_obs)[fold.test_slice]
        assert_embargo(train_idx, test_idx, embargo)  # must not raise


def test_embargo_assertion_fails_when_too_close() -> None:
    train = np.array([0, 1, 2])
    test = np.array([5, 6, 7])
    # train[2] = 2, test[0] = 5 -> gap 3 < embargo 4 => must raise
    with pytest.raises(ValueError):
        assert_embargo(train, test, embargo=4)


def test_purge_embargo_mask_drops_window() -> None:
    mask = purge_embargo_train_mask(
        n_obs=100,
        test_bounds=[(50, 60)],
        embargo=5,
        purge_before=10,
    )
    # rows 40..65 excluded; rows outside retained
    assert not mask[40:65].any()
    assert mask[:40].all()
    assert mask[65:].all()


def test_combinatorial_splits_count() -> None:
    folds = combinatorial_splits(n_obs=900, n_groups=9, n_test_groups=3)
    assert len(folds) == 84  # C(9,3)


def test_cscv_pbo_low_for_consistent_strategy() -> None:
    rng = np.random.default_rng(0)
    # One config consistently better OOS -> low PBO
    t, n = 400, 4
    matrix = rng.normal(0.0005, 0.01, (t, n))
    matrix[:, 0] += 0.0008  # config 0 has persistent edge
    pbo = cscv_pbo(matrix, n_splits=8)
    assert 0.0 <= pbo <= 1.0


def test_psr_high_for_positive_sharpe() -> None:
    rng = np.random.default_rng(1)
    returns = rng.normal(0.001, 0.01, 500)
    assert psr(returns, sr_star=0.0) > 0.9


def test_expected_max_sharpe_increases_with_trials() -> None:
    sr = np.array([0.5, 0.6, 0.55, 0.52])
    assert expected_max_sharpe(sr, 2) <= expected_max_sharpe(sr, 50)


def test_dsr_deflates_with_more_trials() -> None:
    rng = np.random.default_rng(2)
    returns = rng.normal(0.0002, 0.01, 400)  # small edge
    sr_estimates = np.array([0.2, 0.3, 0.25])
    low = dsr(returns, sr_estimates, n_trials=3)
    high = dsr(returns, sr_estimates, n_trials=200)
    assert high < low


def test_build_trust_report_produces_canonical_shape() -> None:
    rng = np.random.default_rng(3)
    n = 700
    index = pd.date_range("2020-01-01", periods=n, tz="Asia/Kolkata", name="date")
    close = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.01, n)))
    returns = pd.Series(np.diff(np.log(close)), index=index[1:])

    def runner(cfg: dict) -> pd.Series:
        # deterministic variation per config so the grid is non-degenerate
        scale = cfg.get("scale", 1.0)
        return returns * scale

    configs = [{"scale": 1.0}, {"scale": 0.9}, {"scale": 1.1}]
    report = build_trust_report(returns, runner, configs, n_folds=3)
    assert report.method == "walk_forward"
    assert 1 <= report.n_folds <= 3
    assert report.embargo_bars == max(200, 20)
    assert report.pbo is not None and 0.0 <= report.pbo <= 1.0
    assert report.deflated_sharpe is not None and 0.0 <= report.deflated_sharpe <= 1.0
    assert report.out_of_sample_sharpe is not None
    assert len(report.caveats) > 0

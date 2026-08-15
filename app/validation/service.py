"""Assemble a TrustReport for a backtest from walk-forward, PBO, and DSR.

The service runs the requested strategy across an expanding walk-forward window,
builds a per-config return matrix over a small strategy×params grid for PBO/DSR,
and packs everything into the canonical ``TrustReport`` schema.

Pure compute over an already-loaded features frame; no I/O. The caller (API /
worker) supplies the features and the per-config backtest runner.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from app.schemas import TrustReport
from app.validation.dsr import dsr
from app.validation.pbo import cscv_pbo
from app.validation.walk_forward import expanding_windows, oos_returns

# Default embargo covers the longest rolling feature window (sma_200). Per
# ADR D-3, it is configurable but defaults to max(200, label_horizon).
DEFAULT_EMBARGO = 200
DEFAULT_HORIZON = 20

Runner = Callable[[dict], pd.Series]


def _per_config_returns(runner: Runner, configs: list[dict]) -> np.ndarray:
    """Build a T×N matrix of per-config daily returns for PBO/DSR."""
    series = [runner(cfg) for cfg in configs]
    series = [s.astype(float).dropna() for s in series if s is not None and len(s) > 1]
    if not series:
        raise ValueError("no usable config return series")
    index = series[0].index
    aligned = [s.reindex(index).ffill().fillna(0.0).to_numpy() for s in series]
    return np.column_stack(aligned)


def build_trust_report(
    returns: pd.Series,
    runner: Runner,
    configs: list[dict],
    n_folds: int = 5,
    embargo: int = DEFAULT_EMBARGO,
    label_horizon: int = DEFAULT_HORIZON,
    periods_per_year: int = 252,
) -> TrustReport:
    """Build a TrustReport for the given strategy return series and grid.

    Parameters
    ----------
    returns:
        Daily return series of the strategy over the full sample.
    runner:
        Callable ``config -> daily return Series``, used to build the PBO matrix.
    configs:
        List of strategy×params configs for the multiple-testing guard.
    n_folds:
        Number of walk-forward folds.
    embargo:
        Minimum train/test gap in rows (enforced).
    label_horizon:
        Forward-return label horizon; combined with ``embargo``.
    """
    embargo = max(embargo, label_horizon)
    folds = expanding_windows(len(returns), n_folds=n_folds, gap=embargo)
    oos = oos_returns(returns, folds)
    oos_clean = [s.dropna() for s in oos]
    oos_sharpe_values = [
        float((s.mean() / s.std(ddof=1)) * np.sqrt(periods_per_year))
        if len(s) > 1 and s.std(ddof=1)
        else 0.0
        for s in oos_clean
    ]
    oos_sharpe = float(np.mean(oos_sharpe_values))

    matrix = _per_config_returns(runner, configs)
    pbo = cscv_pbo(matrix)
    sr_estimates = (
        matrix.mean(axis=0) / (matrix.std(axis=0, ddof=1) + 1e-12) * np.sqrt(periods_per_year)
    )
    deflated = dsr(
        returns.to_numpy(),
        sharpe_estimates=sr_estimates,
        n_trials=len(configs),
        periods_per_year=periods_per_year,
    )
    expected_max = expected_max_sharpe(sr_estimates, len(configs))

    return TrustReport(
        method="walk_forward",
        n_folds=len(folds),
        out_of_sample_sharpe=oos_sharpe,
        pbo=pbo,
        deflated_sharpe=deflated,
        expected_max_sharpe=expected_max,
        embargo_bars=embargo,
        caveats=_caveats(pbo, deflated),
    )


def expected_max_sharpe(sr_estimates: np.ndarray, n_trials: int) -> float:
    from app.validation.dsr import expected_max_sharpe as _ems

    return _ems(sr_estimates, n_trials)


def _caveats(pbo: float, deflated: float) -> list[str]:
    out: list[str] = []
    if pbo >= 0.5:
        out.append(
            "PBO is high (>0.5): the in-sample best configuration frequently "
            "underperforms out-of-sample. Treat headline metrics cautiously."
        )
    if deflated < 0.95:
        out.append(
            "DSR < 0.95: the Sharpe may be within the range expected from "
            "multiple trials; the edge is not strongly evidenced."
        )
    out.append("Net-of-costs assumptions apply; past performance does not predict future results.")
    return out

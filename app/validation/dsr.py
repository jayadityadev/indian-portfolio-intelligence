"""Deflated Sharpe Ratio (DSR) and Probabilistic Sharpe Ratio (PSR).

DSR (Bailey & López de Prado 2014) adjusts the Probabilistic Sharpe Ratio for
the multiplicity of trials: it compares the observed Sharpe to an "expected max
Sharpe" benchmark derived from the number of independent trials and the variance
of the trial Sharpe estimates. A DSR near 1 means the strategy's Sharpe is very
unlikely to be the artefact of multiple-testing luck (paper #12 §2.5.2).

Pure NumPy implementation; unit-testable with synthetic return series.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.special import erfinv


def _skewness(x: np.ndarray) -> float:
    n = x.size
    if n < 3:
        return 0.0
    mean = x.mean()
    m2 = ((x - mean) ** 2).sum() / n
    m3 = ((x - mean) ** 3).sum() / n
    if m2 <= 0:
        return 0.0
    return float(m3 / m2**1.5)


def _kurtosis(x: np.ndarray) -> float:
    n = x.size
    if n < 4:
        return 3.0
    mean = x.mean()
    m2 = ((x - mean) ** 2).sum() / n
    m4 = ((x - mean) ** 4).sum() / n
    if m2 <= 0:
        return 3.0
    return float(m4 / m2**2)


def psr(
    returns: np.ndarray,
    sr_star: float = 0.0,
    rf: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """Probabilistic Sharpe Ratio: P(true Sharpe > sr_star | returns).

    Adjusted for skewness and kurtosis (Bailey & López de Prado 2012).
    """
    x = np.asarray(returns, dtype=float)
    if x.size < 2 or float(np.std(x, ddof=1)) == 0.0:
        return 0.5
    t = x.size
    sr = (x.mean() - rf) / float(np.std(x, ddof=1))
    annualized = sr * math.sqrt(periods_per_year)
    skew = _skewness(x)
    kurt = _kurtosis(x)
    denominator = math.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr**2)
    if denominator <= 0:
        return 0.5
    z = (annualized - sr_star) * math.sqrt(t - 1) / denominator
    return float(0.5 * (1 + math.erf(z / math.sqrt(2))))


def expected_max_sharpe(
    sharpe_estimates: np.ndarray,
    n_trials: int,
    var_trials: float | None = None,
    euler_gamma: float = 0.5772156649015329,
) -> float:
    """Expected maximum Sharpe among ``n_trials`` independent trials.

    Uses the extreme-value formula from Bailey & López de Prado with the
    Euler-Mascheroni constant (paper #12 Eq. 2.29).
    """
    if n_trials <= 1:
        return 0.0
    if var_trials is None:
        var_trials = float(np.var(sharpe_estimates, ddof=1)) if sharpe_estimates.size > 1 else 0.0
    std = math.sqrt(max(var_trials, 0.0))
    term = (1 - euler_gamma) * _inv_norm_cdf(1 - 1.0 / n_trials)
    term += euler_gamma * _inv_norm_cdf(1 - 1.0 / (math.e * n_trials))
    return float(std * term)


def _inv_norm_cdf(p: float) -> float:
    """Inverse standard-normal CDF."""
    if p <= 0.0:
        return -10.0
    if p >= 1.0:
        return 10.0
    return float(math.sqrt(2) * float(erfinv(2 * p - 1)))


def dsr(
    returns: np.ndarray,
    sharpe_estimates: np.ndarray,
    n_trials: int,
    rf: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """Deflated Sharpe Ratio: PSR with the expected-max-Sharpe benchmark."""
    sr_star = expected_max_sharpe(sharpe_estimates, n_trials)
    return psr(returns, sr_star=sr_star, rf=rf, periods_per_year=periods_per_year)

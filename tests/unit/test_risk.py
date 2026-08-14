import pandas as pd
import pytest
from fixtures.data import make_ohlcv

from app.risk.report import compute_risk_report
from app.risk.var import expected_shortfall, historical_var, max_drawdown_pct, parametric_var
from app.risk.volatility import annualized_ewma_volatility


def test_tail_risk_estimators_match_known_returns() -> None:
    returns = pd.Series([-0.10, -0.05, 0.01, 0.02, 0.03])
    assert historical_var(returns, 0.95) == pytest.approx(0.09)
    assert expected_shortfall(returns, 0.95) == pytest.approx(0.10)
    assert parametric_var(returns, 0.95) > 0


def test_ewma_and_drawdown() -> None:
    close = pd.Series([100.0, 110.0, 99.0, 120.0])
    returns = close.pct_change().dropna()
    assert annualized_ewma_volatility(returns) >= 0
    assert max_drawdown_pct(close) == pytest.approx(10.0)


def test_risk_report_matches_schema() -> None:
    close = make_ohlcv()["close"]
    report = compute_risk_report("TEST.NS", close)
    assert report.symbol == "TEST.NS"
    assert report.method == "ewma"
    assert report.annualized_vol_pct >= 0
    assert report.var_95_pct >= 0
    assert report.var_99_pct >= report.var_95_pct

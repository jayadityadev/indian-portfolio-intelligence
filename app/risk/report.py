"""Risk report assembly."""

from __future__ import annotations

import pandas as pd

from app.risk.var import expected_shortfall, historical_var, max_drawdown_pct
from app.risk.volatility import annualized_ewma_volatility
from app.schemas import RiskReport


def compute_risk_report(symbol: str, close: pd.Series) -> RiskReport:
    """Compute canonical one-day EWMA and tail-risk report."""
    returns = close.astype(float).pct_change().dropna()
    annualized = annualized_ewma_volatility(returns)
    return RiskReport(
        symbol=symbol,
        method="ewma",
        annualized_vol_pct=annualized * 100,
        ewma_vol_pct=annualized * 100,
        var_95_pct=historical_var(returns, 0.95) * 100,
        var_99_pct=historical_var(returns, 0.99) * 100,
        expected_shortfall_95_pct=expected_shortfall(returns, 0.95) * 100,
        max_drawdown_pct=max_drawdown_pct(close),
    )

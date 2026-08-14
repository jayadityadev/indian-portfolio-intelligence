"""Configurable Indian cash-equity transaction costs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IndianCostModel:
    """Per-side costs expressed as decimal fractions of traded notional."""

    brokerage_pct: float = 0.0003
    stt_pct: float = 0.001
    stamp_pct: float = 0.00015
    exchange_txn_pct: float = 0.0000325
    slippage_pct: float = 0.0005

    @property
    def per_side_pct(self) -> float:
        return self.brokerage_pct + self.stamp_pct + self.exchange_txn_pct + self.slippage_pct

    @property
    def round_trip_pct(self) -> float:
        return 2 * self.per_side_pct + self.stt_pct


def net_trade_pnl(gross_pnl_pct: float, cost_model: IndianCostModel | None = None) -> float:
    """Subtract round-trip costs from a long trade's percentage P&L."""
    model = cost_model or IndianCostModel()
    return gross_pnl_pct - model.round_trip_pct * 100


def apply_costs_to_returns(
    returns: Any,
    turnover: Any,
    cost_model: IndianCostModel | None = None,
) -> Any:
    """Subtract costs from daily returns according to daily turnover.

    Objects are intentionally duck-typed so pandas Series retain their index and
    callers do not need a second dependency abstraction.
    """
    model = cost_model or IndianCostModel()
    return returns - turnover * model.per_side_pct

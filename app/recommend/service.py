"""Recommendation assembly service."""

from __future__ import annotations

from app.recommend.scoring import best_strategy, score_strategies
from app.schemas import Recommendation, RegimeResult, StrategyName


def recommend(
    symbol: str,
    regime: RegimeResult,
    evidence: dict[StrategyName, float] | None = None,
) -> Recommendation:
    """Build educational strategy guidance from current regime and evidence."""
    current_state = regime.labels[-1] if regime.labels else 1
    state_name = regime.state_names.get(current_state, "sideways")
    suitability = score_strategies(state_name, evidence)
    suggested = best_strategy(suitability)
    return Recommendation(
        symbol=symbol,
        current_regime={"state_name": state_name, "confidence": _confidence(regime)},
        suggested_strategy=suggested,
        rationale=_rationale(state_name, suggested),
        suitability=suitability,
        caveat=(
            "Not investment advice. Backtests are educational and past performance "
            "does not predict future results."
        ),
    )


def _confidence(regime: RegimeResult) -> float:
    if not regime.labels:
        return 0.0
    recent = regime.labels[-20:]
    return round(recent.count(recent[-1]) / len(recent), 3)


def _rationale(regime: str, strategy: StrategyName) -> list[str]:
    rationale = {
        "bull": "Trend-following strategies can participate while positive returns persist.",
        "bear": (
            "Risk control matters in falling markets; avoid treating a regime label "
            "as a timing guarantee."
        ),
        "sideways": (
            "Range-bound conditions can favour mean-reversion signals, subject to "
            "costs and execution."
        ),
    }
    return [
        rationale.get(regime, rationale["sideways"]),
        f"Current rule-based suitability favours {strategy}.",
    ]

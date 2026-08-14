"""Regime-to-strategy suitability scoring."""

from __future__ import annotations

from app.schemas import StrategyName

STRATEGIES: tuple[StrategyName, ...] = (
    "buy_and_hold",
    "ma_crossover",
    "rsi",
    "momentum",
    "mean_reversion",
)

SUITABILITY: dict[str, dict[StrategyName, float]] = {
    "bull": {
        "buy_and_hold": 0.85,
        "ma_crossover": 0.80,
        "rsi": 0.35,
        "momentum": 0.90,
        "mean_reversion": 0.30,
    },
    "bear": {
        "buy_and_hold": 0.20,
        "ma_crossover": 0.55,
        "rsi": 0.45,
        "momentum": 0.15,
        "mean_reversion": 0.65,
    },
    "sideways": {
        "buy_and_hold": 0.35,
        "ma_crossover": 0.30,
        "rsi": 0.80,
        "momentum": 0.25,
        "mean_reversion": 0.85,
    },
}


def score_strategies(
    regime: str, evidence: dict[StrategyName, float] | None = None
) -> dict[str, float]:
    """Return suitability scores, optionally blended with validated evidence."""
    scores: dict[str, float] = {
        strategy: score
        for strategy, score in SUITABILITY.get(regime, SUITABILITY["sideways"]).items()
    }
    if evidence:
        for strategy, score in evidence.items():
            if strategy in scores:
                scores[strategy] = round(0.7 * scores[strategy] + 0.3 * score, 4)
    return scores


def best_strategy(scores: dict[str, float]) -> StrategyName:
    return max(STRATEGIES, key=lambda strategy: scores.get(strategy, float("-inf")))

"""Cross-source data integrity check.

Owner: Chirag.

Spot-checks a sample of symbols against a third source (Twelve Data, if
TWELVEDATA_API_KEY is set) and validates raw-vs-adjusted consistency (split and
bonus handling). Fails loudly on anomalies — an unadjusted series silently
corrupts every downstream backtest.

Run:  make validate-data
"""

from __future__ import annotations


def main() -> None:
    raise NotImplementedError(
        "Validation not implemented yet. See app/data/adjust.py and "
        "docs/IMPLEMENTATION_PLAN.md §9.2."
    )


if __name__ == "__main__":
    main()

"""Seed the parquet cache for the NIFTY-50 universe.

Owner: Chirag.

Backfills ~20 years of split/dividend-adjusted daily OHLCV for the NIFTY-50
index + constituents via the ``app.data`` layer (yfinance primary, nsepython
fallback), writes one parquet per symbol plus a manifest, and populates the
Postgres ``symbols`` table.

Run:  make seed   (or `python -m scripts.seed_universe` inside the worker container)
"""

from __future__ import annotations


def main() -> None:
    raise NotImplementedError(
        "Seed pipeline not implemented yet. See app/data/ (sources.py, cache.py, "
        "universe.py) and docs/IMPLEMENTATION_PLAN.md §9 + §17 T1."
    )


if __name__ == "__main__":
    main()

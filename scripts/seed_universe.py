"""Seed the parquet cache for the NIFTY-50 universe.

Owner: Chirag.

Backfills ~20 years of split/dividend-adjusted daily OHLCV for the NIFTY-50
index + constituents via the ``app.data`` layer (yfinance primary, nsepython
fallback), writes one parquet per symbol plus a manifest, and populates the
Postgres ``symbols`` table (best-effort).

Run:  make seed   (or `python -m scripts.seed_universe` inside the worker container)
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.data import cache, db
from app.data.metadata import symbol_info
from app.data.sources import fetch
from app.data.universe import nifty50_index, nifty50_symbols


@dataclass
class SeedSummary:
    ok: int = 0
    failed: int = 0
    failures: dict[str, str] = field(default_factory=dict)

    def record_ok(self) -> None:
        self.ok += 1

    def record_failure(self, symbol: str, message: str) -> None:
        self.failed += 1
        self.failures[symbol] = message


def seed_one(symbol: str, start: date, end: date) -> None:
    """Fetch ``[start, end]`` and write to the parquet cache for one symbol."""
    cache.store(fetch(symbol, start, end))


def seed_symbols(symbols: list[str], start: date, end: date) -> SeedSummary:
    summary = SeedSummary()
    for symbol in symbols:
        try:
            seed_one(symbol, start, end)
        except Exception as exc:  # noqa: BLE001 — a failed symbol must not abort the run
            summary.record_failure(symbol, str(exc))
            print(f"FAIL {symbol}: {exc}", file=sys.stderr)
        else:
            summary.record_ok()
            print(f"  ok {symbol}")
    return summary


def seed_postgres(symbols: list[str]) -> None:
    """Populate the Postgres ``symbols`` table (best-effort)."""
    db.create_schema()
    db.upsert_symbols([symbol_info(symbol) for symbol in symbols])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=20, help="lookback window in years")
    parser.add_argument("--limit", type=int, default=0, help="seed only the first N symbols")
    parser.add_argument("--symbols", nargs="*", default=None, help="explicit symbol list override")
    args = parser.parse_args()

    symbols = nifty50_symbols() + [nifty50_index()]
    if args.symbols:
        symbols = args.symbols
    if args.limit:
        symbols = symbols[: args.limit]

    end = date.today()
    start = end - timedelta(days=365 * args.years)

    print(f"Seeding {len(symbols)} symbols over {args.years} years (since {start})")
    summary = seed_symbols(symbols, start, end)

    try:
        seed_postgres(symbols)
    except Exception as exc:  # noqa: BLE001 — metadata store must not fail the seed
        print(f"WARN postgres symbols not populated: {exc}", file=sys.stderr)
    else:
        print(f"Postgres symbols upserted: {len(symbols)} rows")

    print(f"\nSeed complete: {summary.ok} ok, {summary.failed} failed")
    if summary.failed >= summary.ok:
        print("ERROR: more symbols failed than succeeded.", file=sys.stderr)
        raise SystemExit(1)
    if not args.symbols and not args.limit and summary.ok < 20:
        print(
            "ERROR: fewer than 20 symbols seeded — check network/source errors above.",
            file=sys.stderr,
        )  # noqa: E501
        raise SystemExit(1)


if __name__ == "__main__":
    main()

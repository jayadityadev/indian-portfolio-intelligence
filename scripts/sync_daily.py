"""Daily incremental sync: append new trading days to the parquet cache.

Owner: Chirag.

Checks the last date in each symbol's parquet, fetches only newer rows, appends,
and updates the manifest hash. Safe to re-run; idempotent.

Run:  make sync
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta

import pandas as pd

from app.data import cache
from app.data.sources import fetch
from app.data.universe import nifty50_index, nifty50_symbols
from app.schemas import MarketDataFrame


def sync_one(symbol: str, today: date | None = None) -> int:
    """Append rows newer than the cached latest date. Returns rows appended (0 if none)."""
    today = today or date.today()
    last = cache.latest_date(symbol)
    if last is None:
        return 0  # not seeded yet; run seed_universe first
    if last >= today - timedelta(days=1):
        return 0  # already current (market may be closed on weekends/holidays)

    start = last + timedelta(days=1)
    try:
        data = fetch(symbol, start, today)
    except Exception:  # noqa: BLE001 — no new rows is a normal, idempotent outcome
        return 0
    if data.frame.empty:
        return 0

    try:
        existing = cache.load(symbol).frame
    except (FileNotFoundError, ValueError):
        return 0  # corrupt cache — re-seed, don't paper over it

    merged = pd.concat([existing, data.frame])
    merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    cache.store(
        MarketDataFrame(
            symbol=symbol,
            source=data.source,
            adjusted=data.adjusted,
            frame=merged,
            fetched_at=data.fetched_at,
        )
    )
    last_ts = pd.Timestamp(last, tz="Asia/Kolkata")
    return int((merged.index > last_ts).sum())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="sync only the first N symbols")
    parser.add_argument("--symbols", nargs="*", default=None, help="explicit symbol list override")
    args = parser.parse_args()

    symbols = nifty50_symbols() + [nifty50_index()]
    if args.symbols:
        symbols = args.symbols
    if args.limit:
        symbols = symbols[: args.limit]

    appended = 0
    for symbol in symbols:
        rows = sync_one(symbol)
        appended += rows
        if rows:
            print(f"  +{rows:4d} {symbol}")

    print(f"Sync complete: {appended} new rows across {len(symbols)} symbols")


if __name__ == "__main__":
    main()

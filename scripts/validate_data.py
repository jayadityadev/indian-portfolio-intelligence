"""Cross-source data integrity check.

Owner: Chirag.

Validates raw-vs-adjusted consistency (split and bonus handling) for every
symbol and, if ``TWELVEDATA_API_KEY`` is set, spot-checks a sample of last
closes against Twelve Data. Fails loudly on anomalies — an unadjusted series
silently corrupts every downstream backtest.

Run:  make validate-data
"""

from __future__ import annotations

import argparse
import sys

import httpx

from app.config import settings
from app.data import cache
from app.data.adjust import AdjustmentReport, validate_adjustment
from app.data.universe import nifty50_index, nifty50_symbols


def validate_one(symbol: str) -> AdjustmentReport:
    """Wrap ``validate_adjustment``; a hard failure still yields a failed report."""
    try:
        return validate_adjustment(symbol)
    except Exception as exc:  # noqa: BLE001 — report the failure, keep validating the rest
        return AdjustmentReport(symbol=symbol, ok=False, detected_events=0, note=str(exc))


def twelvedata_last_close(symbol: str, api_key: str) -> float | None:
    """Return the last daily close from Twelve Data, or None on any error."""
    nse_symbol = symbol.removesuffix(".NS").removesuffix("^NSEI")
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": f"{nse_symbol}:NSE",
        "interval": "1day",
        "outputsize": "1",
        "apikey": api_key,
    }
    try:
        response = httpx.get(url, params=params, timeout=15)
        response.raise_for_status()
        values = response.json().get("values", [])
        if not values:
            return None
        return float(values[0]["close"])
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return None


def cross_check(symbol: str, api_key: str) -> str | None:
    """Compare cached last close against Twelve Data; return an anomaly note or None."""
    try:
        cached_close = float(cache.load(symbol).frame["close"].iloc[-1])
    except (FileNotFoundError, ValueError):
        return None
    remote_close = twelvedata_last_close(symbol, api_key)
    if remote_close is None:
        return None
    divergence = abs(cached_close - remote_close) / remote_close
    if divergence > 0.05:
        return (
            f"last close diverges {divergence:.2%} vs Twelve Data "
            f"(cached {cached_close:.2f}, remote {remote_close:.2f})"
        )
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="validate only the first N symbols")
    parser.add_argument("--symbols", nargs="*", default=None, help="explicit symbol list override")
    args = parser.parse_args()

    symbols = nifty50_symbols() + [nifty50_index()]
    if args.symbols:
        symbols = args.symbols
    if args.limit:
        symbols = symbols[: args.limit]

    failed: dict[str, str] = {}
    events = 0
    for symbol in symbols:
        report = validate_one(symbol)
        if not report.ok:
            failed[symbol] = report.note or "invalid raw/adjusted ratio"
            print(f"FAIL {symbol}: {failed[symbol]}", file=sys.stderr)
        else:
            events += report.detected_events
            print(f"  ok {symbol} ({report.detected_events} adjustment events)")

    if settings.twelvedata_api_key:
        print("Twelve Data spot-check enabled")
        for symbol in symbols[:10]:
            note = cross_check(symbol, settings.twelvedata_api_key)
            if note:
                failed.setdefault(symbol, note)
                print(f"FAIL {symbol}: {note}", file=sys.stderr)

    ok = len(symbols) - len(failed)
    print(f"\nValidation complete: {ok} ok, {len(failed)} failed, {events} adjustment events")
    if failed:
        print("ERROR: validation flagged unadjusted or anomalous series.", file=sys.stderr)
        raise SystemExit(1)
    if not args.symbols and not args.limit and ok < 20:
        print("ERROR: validation did not pass for the full universe.", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

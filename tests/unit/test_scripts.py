from __future__ import annotations

from datetime import date

import pandas as pd

from app.data import cache
from app.data.metadata import INDEX_SYMBOL, symbol_info
from app.schemas import MarketDataFrame
from scripts.seed_universe import seed_one
from scripts.sync_daily import sync_one


def _frame(days: int, start: date = date(2025, 1, 1)) -> pd.DataFrame:
    index = pd.date_range(start, periods=days, tz="Asia/Kolkata", name="date")
    return pd.DataFrame(
        {
            "open": [1.0] * days,
            "high": [2.0] * days,
            "low": [0.5] * days,
            "close": [1.5] * days,
            "volume": [10.0] * days,
        },
        index=index,
        dtype=float,
    )


def _md(symbol: str, frame: pd.DataFrame) -> MarketDataFrame:
    return MarketDataFrame(symbol=symbol, source="yfinance", adjusted=True, frame=frame)


def test_seed_one_stores_and_manifest_is_valid(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cache.settings, "parquet_dir", str(tmp_path))
    monkeypatch.setattr(
        "scripts.seed_universe.fetch",
        lambda symbol, start, end: _md(symbol, _frame(5)),
    )
    seed_one("TEST.NS", date(2025, 1, 1), date(2025, 1, 5))
    assert cache.latest_date("TEST.NS") == date(2025, 1, 5)
    assert cache.manifest_is_valid("TEST.NS")


def test_sync_one_appends_newer_rows_idempotently(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cache.settings, "parquet_dir", str(tmp_path))
    cache.store(_md("TEST.NS", _frame(5)))

    fetched: list[tuple[date, date]] = []

    def fake_fetch(symbol: str, start: date, end: date) -> MarketDataFrame:
        fetched.append((start, end))
        return _md(symbol, _frame(2, start=date(2025, 1, 6)))

    monkeypatch.setattr("scripts.sync_daily.fetch", fake_fetch)

    appended = sync_one("TEST.NS", today=date(2025, 1, 7))
    assert appended == 2
    assert cache.latest_date("TEST.NS") == date(2025, 1, 7)

    cache_after_first = cache.load("TEST.NS").frame
    appended_again = sync_one("TEST.NS", today=date(2025, 1, 7))
    assert appended_again == 0
    pd.testing.assert_frame_equal(cache.load("TEST.NS").frame, cache_after_first)


def test_metadata_covers_full_universe() -> None:
    from app.data.universe import nifty50_symbols

    rows = [symbol_info(symbol) for symbol in nifty50_symbols() + [INDEX_SYMBOL]]
    assert len(rows) == 51
    assert all(row.name for row in rows)
    assert all(row.exchange == "NSE" for row in rows)
    assert symbol_info("RELIANCE.NS").sector == "Energy"
    assert symbol_info(INDEX_SYMBOL).index_member is False
    assert all(row.index_member for row in rows if row.symbol != INDEX_SYMBOL)

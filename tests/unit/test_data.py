from datetime import date

import pandas as pd

from app.data import cache
from app.data.universe import nifty50_index, nifty50_symbols
from app.schemas import MarketDataFrame


def test_universe_is_deterministic_and_nse_formatted() -> None:
    symbols = nifty50_symbols()
    assert len(symbols) == 50
    assert all(symbol.endswith(".NS") for symbol in symbols)
    assert nifty50_index() == "^NSEI"


def test_cache_store_load_and_manifest(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cache.settings, "parquet_dir", str(tmp_path))
    index = pd.date_range("2025-01-01", periods=3, tz="Asia/Kolkata", name="date")
    frame = pd.DataFrame(
        {
            "open": [1, 2, 3],
            "high": [2, 3, 4],
            "low": [0, 1, 2],
            "close": [1.5, 2.5, 3.5],
            "volume": [10, 20, 30],
        },
        index=index,
        dtype=float,
    )
    cache.store(MarketDataFrame("TEST.NS", "yfinance", True, frame))
    assert cache.latest_date("TEST.NS") == date(2025, 1, 3)
    assert cache.manifest_is_valid("TEST.NS")
    loaded = cache.load("TEST.NS")
    pd.testing.assert_frame_equal(loaded.frame, frame)

    loaded.frame.iloc[0, 0] = 999
    loaded.frame.to_parquet(tmp_path / "TEST.NS.parquet")
    assert not cache.manifest_is_valid("TEST.NS")

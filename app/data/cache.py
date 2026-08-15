"""Parquet cache + manifest.

Owner: Jayaditya (interface) / Chirag (seed+sync scripts use this).

Contract (frozen for Chirag's scripts):
    load(symbol) -> MarketData          # read from parquet, never hits network
    store(md: MarketData) -> None       # write parquet + update manifest
    latest_date(symbol) -> date | None  # last stored date (for incremental sync)
    manifest_is_valid(symbol) -> bool   # hash check; corrupt -> re-seed
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import cast

import pandas as pd

from app.config import settings
from app.schemas import OHLCV_COLUMNS, MarketDataFrame


def _root() -> Path:
    root = Path(settings.parquet_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path(symbol: str) -> Path:
    safe = symbol.replace("^", "index_").replace("/", "_")
    return _root() / f"{safe}.parquet"


def _manifest_path() -> Path:
    return _root() / "manifest.json"


def _read_manifest() -> dict[str, dict[str, object]]:
    path = _manifest_path()
    if not path.exists():
        return {}
    return cast(dict[str, dict[str, object]], json.loads(path.read_text()))


def _write_manifest(manifest: dict[str, dict[str, object]]) -> None:
    _manifest_path().write_text(json.dumps(manifest, indent=2, sort_keys=True))


def load(symbol: str) -> MarketDataFrame:
    path = _path(symbol)
    if not path.exists():
        raise FileNotFoundError(f"no cached data for {symbol}")
    manifest = _read_manifest().get(symbol)
    if not manifest_is_valid(symbol):
        raise ValueError(f"cached data is corrupt for {symbol}")
    frame = pd.read_parquet(path)
    frame.index = pd.to_datetime(frame.index)
    frame.index.freq = pd.infer_freq(frame.index)
    return MarketDataFrame(
        symbol=symbol,
        source=str((manifest or {}).get("source", "yfinance")),  # type: ignore[arg-type]
        adjusted=bool((manifest or {}).get("adjusted", True)),
        frame=frame.loc[:, OHLCV_COLUMNS],
    )


def store(md: MarketDataFrame) -> None:
    path = _path(md.symbol)
    md.frame.to_parquet(path, index=True)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = _read_manifest()
    manifest[md.symbol] = {
        "sha256": digest,
        "last_updated": md.frame.index.max().date().isoformat(),
        "source": md.source,
        "adjusted": md.adjusted,
    }
    _write_manifest(manifest)


def latest_date(symbol: str) -> date | None:
    path = _path(symbol)
    if not path.exists():
        return None
    frame = pd.read_parquet(path, columns=["close"])
    return cast(date, pd.to_datetime(frame.index).max().date())


def manifest_is_valid(symbol: str) -> bool:
    path = _path(symbol)
    entry = _read_manifest().get(symbol)
    if not path.exists() or not entry:
        return False
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest == entry.get("sha256")

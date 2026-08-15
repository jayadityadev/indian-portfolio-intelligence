"""Data source adapters.

Owner: Jayaditya.

Every source implements the same ``fetch`` interface so no other module knows
(or cares) which source produced the data. Sources:
  - ``yfinance``  : primary (split/dividend adjusted, ``<SYMBOL>.NS`` / ``.BO``)
  - ``nsepython`` : fallback (NSE-native history + fundamentals)
  - ``twelvedata``: optional cross-check only (``<SYMBOL>.NSE``)

Contract (frozen for Chirag's scripts):
    fetch(symbol, start, end, source) -> MarketData
"""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import yfinance as yf

from app.schemas import OHLCV_COLUMNS, MarketDataFrame, SourceName


def fetch(
    symbol: str,
    start: date,
    end: date,
    source: SourceName | None = None,
) -> MarketDataFrame:
    """Return ``MarketData`` for ``symbol`` over ``[start, end]``.

    - ``source=None`` means "auto": try yfinance, fall back to nsepython.
    - Result MUST be split/dividend adjusted (``adjusted=True``).
    - Raises ``DataUnavailableError`` if both sources fail.
    """
    if start > end:
        raise ValueError("start must not be after end")
    if source in (None, "yfinance"):
        try:
            return _fetch_yfinance(symbol, start, end)
        except Exception as exc:
            if source == "yfinance":
                raise DataUnavailableError(f"yfinance failed for {symbol}: {exc}") from exc
            yfinance_error = exc
    else:
        yfinance_error = None

    if source in (None, "nsepython"):
        try:
            return _fetch_nsepython(symbol, start, end)
        except Exception as exc:
            detail = f"; yfinance: {yfinance_error}" if yfinance_error else ""
            raise DataUnavailableError(f"no source returned {symbol}: {exc}{detail}") from exc
    raise DataUnavailableError(f"unsupported source: {source}")


def _normalise_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame = frame.rename(columns={column: column.lower() for column in frame.columns})
    missing = [column for column in OHLCV_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"source response missing columns: {missing}")
    index = pd.to_datetime(frame.index)
    if index.tz is None:
        index = index.tz_localize("Asia/Kolkata")
    else:
        index = index.tz_convert("Asia/Kolkata")
    frame = frame.loc[:, OHLCV_COLUMNS].copy()
    frame.index = index.rename("date")
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    frame = frame.dropna(subset=["close"])
    if frame.empty:
        raise ValueError("source returned no rows")
    return frame.astype(float)


def _fetch_yfinance(symbol: str, start: date, end: date) -> MarketDataFrame:
    frame = yf.download(
        symbol,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    return MarketDataFrame(
        symbol=symbol,
        source="yfinance",
        adjusted=True,
        frame=_normalise_frame(frame),
        fetched_at=datetime.now(),
    )


def _fetch_nsepython(symbol: str, start: date, end: date) -> MarketDataFrame:
    from nsepython import get_history

    nse_symbol = symbol.removesuffix(".NS")
    frame = get_history(
        symbol=nse_symbol,
        start=start.strftime("%d-%m-%Y"),
        end=end.strftime("%d-%m-%Y"),
    )
    frame = frame.rename(
        columns={
            "CH_OPENING_PRICE": "open",
            "CH_TRADE_HIGH_PRICE": "high",
            "CH_TRADE_LOW_PRICE": "low",
            "CH_CLOSING_PRICE": "close",
            "CH_TOT_TRADED_QTY": "volume",
            "mTIMESTAMP": "date",
        }
    )
    if "date" in frame.columns:
        frame = frame.set_index("date")
    return MarketDataFrame(
        symbol=symbol,
        source="nsepython",
        adjusted=True,
        frame=_normalise_frame(frame),
        fetched_at=datetime.now(),
    )


class DataUnavailableError(RuntimeError):
    """Raised when no configured source can return data for a symbol."""

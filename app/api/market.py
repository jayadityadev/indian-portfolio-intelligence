"""Market data endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import load_market_frame
from app.data import cache
from app.data.metadata import symbol_info
from app.data.universe import nifty50_index, nifty50_symbols
from app.schemas import STRATEGY_NAMES

router = APIRouter()


@router.get("/symbols")
def symbols() -> dict[str, object]:
    universe = nifty50_symbols() + [nifty50_index()]
    return {
        "ok": True,
        "data": [
            {
                "symbol": info.symbol,
                "name": info.name,
                "sector": info.sector,
                "index_member": info.index_member,
                "cached": cache.latest_date(info.symbol) is not None,
            }
            for info in (symbol_info(symbol) for symbol in universe)
        ],
    }


@router.get("/strategies")
def strategies() -> dict[str, object]:
    return {"ok": True, "data": list(STRATEGY_NAMES)}


@router.get("/{symbol}/series")
def series(symbol: str) -> dict[str, object]:
    try:
        frame = load_market_frame(symbol)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    records = frame.reset_index().rename(columns={"date": "date"})
    records["date"] = records["date"].dt.date.astype(str)
    records = records.where(records.notna(), None)
    return {"ok": True, "data": records.to_dict(orient="records")}

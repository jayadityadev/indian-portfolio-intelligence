"""Market data endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import load_market_frame
from app.data.universe import nifty50_symbols

router = APIRouter()


@router.get("/symbols")
def symbols() -> dict[str, object]:
    return {
        "ok": True,
        "data": [
            {
                "symbol": symbol,
                "name": symbol.removesuffix(".NS"),
                "sector": None,
                "index_member": True,
            }
            for symbol in nifty50_symbols()
        ],
    }


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

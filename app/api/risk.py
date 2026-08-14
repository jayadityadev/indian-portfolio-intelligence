"""Risk report endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import load_market_frame
from app.risk.report import compute_risk_report

router = APIRouter()


@router.get("/{symbol}")
def risk(symbol: str) -> dict[str, object]:
    try:
        close = load_market_frame(symbol)["close"]
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "data": compute_risk_report(symbol, close).model_dump(mode="json")}

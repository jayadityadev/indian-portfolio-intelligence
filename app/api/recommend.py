"""Recommendation endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import load_features
from app.recommend.service import recommend
from app.regime.hmm import fit_hmm

router = APIRouter()


@router.get("/{symbol}")
def recommendation(symbol: str) -> dict[str, object]:
    try:
        regime = fit_hmm(load_features(symbol), symbol=symbol)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "data": recommend(symbol, regime).model_dump(mode="json")}

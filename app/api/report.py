"""Thin chart JSON endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import load_features, load_market_frame
from app.regime.hmm import fit_hmm
from app.report import charts
from app.schemas import BacktestResult, CompareReport, Recommendation, RegimeResult

router = APIRouter()


class PriceRegimeRequest(BaseModel):
    records: list[dict[str, Any]]
    regime: RegimeResult


@router.get("/{symbol}/equity")
def equity(symbol: str) -> dict[str, object]:
    try:
        frame = load_market_frame(symbol)
        regime = fit_hmm(load_features(symbol), symbol=symbol)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    records = frame.reset_index().to_dict(orient="records")
    return {"ok": True, "data": charts.price_with_regime(records, regime)}


@router.post("/price-regime")
def price_regime(request: PriceRegimeRequest) -> dict[str, object]:
    return {"ok": True, "data": charts.price_with_regime(request.records, request.regime)}


@router.post("/backtest")
def backtest_chart(result: BacktestResult) -> dict[str, object]:
    return {
        "ok": True,
        "data": {
            "equity": charts.equity_vs_benchmark(result),
            "drawdown": charts.drawdown(result),
            "trades": charts.trade_scatter(result),
        },
    }


@router.post("/compare")
def compare_chart(report: CompareReport) -> dict[str, object]:
    return {"ok": True, "data": charts.strategy_comparison(report)}


@router.post("/suitability")
def suitability_chart(recommendation: Recommendation) -> dict[str, object]:
    return {"ok": True, "data": charts.suitability_bars(recommendation)}

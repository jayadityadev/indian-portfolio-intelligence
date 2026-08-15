"""Iteration-1 Streamlit client for the FastAPI platform."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
import plotly.io as pio
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8888").rstrip("/")

st.set_page_config(page_title="Portfolio Intelligence", layout="wide")


def api_get(path: str) -> Any:
    response = httpx.get(f"{API_URL}{path}", timeout=30)
    response.raise_for_status()
    body = response.json()
    if not body.get("ok", False):
        raise RuntimeError(body.get("error", {}).get("message", "API request failed"))
    return body["data"]


def api_post(path: str, payload: dict[str, Any]) -> Any:
    response = httpx.post(f"{API_URL}{path}", json=payload, timeout=30)
    response.raise_for_status()
    body = response.json()
    if not body.get("ok", False):
        raise RuntimeError(body.get("error", {}).get("message", "API request failed"))
    return body["data"]


def render_chart(chart_json: str, key: str) -> None:
    st.plotly_chart(pio.from_json(chart_json), use_container_width=True, key=key)


def poll_job(job_id: str) -> Any:
    progress = st.progress(0)
    with st.status("Running backend job", expanded=False) as status:
        for _ in range(120):
            job = api_get(f"/api/v1/jobs/{job_id}")
            progress.progress(min(max(job.get("progress_pct") or 0, 0), 100))
            if job["status"] == "succeeded":
                status.update(label="Job complete", state="complete")
                return api_get(f"/api/v1/jobs/{job_id}/result")
            if job["status"] == "failed":
                status.update(label="Job failed", state="error")
                st.error(job.get("error") or "Backend job failed")
                return None
            time.sleep(1)
        status.update(label="Job timed out", state="error")
        st.error("Backend job timed out")
    return None


def choose_symbol(symbols: list[dict[str, Any]]) -> str:
    names = [item["symbol"] for item in symbols]
    return st.sidebar.selectbox("Symbol", names, index=names.index("^NSEI") if "^NSEI" in names else 0)


def market_page(symbol: str) -> None:
    st.header("Market")
    try:
        records = api_get(f"/api/v1/market/{symbol}/series")
        chart = api_get(f"/api/v1/report/{symbol}/equity")
        if records:
            latest = records[-1]
            st.metric("Latest close", f"{latest.get('close', 0):,.2f}")
            st.caption(f"{len(records):,} cached daily observations")
        render_chart(chart, "market-price")
    except Exception as exc:
        st.error(str(exc))


def backtest_page(symbol: str, strategies: list[str]) -> None:
    st.header("Backtest")
    strategy = st.selectbox("Strategy", strategies)
    net_of_costs = st.checkbox("Net of Indian transaction costs", value=True)
    if st.button("Run backtest"):
        try:
            job = api_post(
                "/api/v1/backtest",
                {"symbol": symbol, "strategy": strategy, "net_of_costs": net_of_costs},
            )
            result = poll_job(job["job_id"])
            if result:
                charts = api_post("/api/v1/report/backtest", result)
                render_chart(charts["equity"], "backtest-equity")
                render_chart(charts["drawdown"], "backtest-drawdown")
                st.dataframe(result["metrics"], use_container_width=True)
        except Exception as exc:
            st.error(str(exc))
    if st.button("Compare all strategies"):
        try:
            job = api_post(
                "/api/v1/backtest/compare",
                {"symbol": symbol, "strategies": strategies, "net_of_costs": net_of_costs},
            )
            result = poll_job(job["job_id"])
            if result:
                render_chart(api_post("/api/v1/report/compare", result), "strategy-comparison")
        except Exception as exc:
            st.error(str(exc))


def regime_page(symbol: str) -> None:
    st.header("Regime")
    try:
        regime = api_get(f"/api/v1/regime/{symbol}/timeline")
        chart = api_get(f"/api/v1/report/{symbol}/equity")
        state = regime["state_names"].get(str(regime["labels"][-1]), "unknown")
        st.metric("Current regime", state)
        render_chart(chart, "regime-price")
        st.json(regime["validation"])
    except Exception as exc:
        st.error(str(exc))


def risk_page(symbol: str) -> None:
    st.header("Risk")
    try:
        risk = api_get(f"/api/v1/risk/{symbol}")
        columns = st.columns(4)
        columns[0].metric("Annualized EWMA vol", f"{risk['annualized_vol_pct']:.2f}%")
        columns[1].metric("VaR 95%", f"{risk['var_95_pct']:.2f}%")
        columns[2].metric("Expected shortfall", f"{risk['expected_shortfall_95_pct']:.2f}%")
        columns[3].metric("Max drawdown", f"{risk['max_drawdown_pct']:.2f}%")
        st.json(risk)
    except Exception as exc:
        st.error(str(exc))


def recommend_page(symbol: str) -> None:
    st.header("Recommend")
    try:
        recommendation = api_get(f"/api/v1/recommend/{symbol}")
        st.metric("Suggested strategy", recommendation["suggested_strategy"])
        st.write(recommendation["rationale"])
        render_chart(
            api_post("/api/v1/report/suitability", recommendation),
            "suitability",
        )
        st.warning(recommendation["caveat"])
    except Exception as exc:
        st.error(str(exc))


try:
    symbols = api_get("/api/v1/market/symbols")
    strategies = api_get("/api/v1/market/strategies")
    symbol = choose_symbol(symbols)
    page = st.sidebar.radio("Page", ["Market", "Backtest", "Regime", "Risk", "Recommend"])
    if page == "Market":
        market_page(symbol)
    elif page == "Backtest":
        backtest_page(symbol, strategies)
    elif page == "Regime":
        regime_page(symbol)
    elif page == "Risk":
        risk_page(symbol)
    else:
        recommend_page(symbol)
except (httpx.HTTPError, RuntimeError, KeyError, ValueError) as exc:
    st.error(f"Cannot reach portfolio API at {API_URL}: {exc}")

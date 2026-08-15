"""Iteration-1 Streamlit client for the FastAPI portfolio intelligence platform."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
import plotly.io as pio

import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8888").rstrip("/")

st.set_page_config(
    page_title="Indian Portfolio Intelligence",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


class ApiError(Exception):
    """Raised on non-OK envelope responses."""


def api_get(path: str) -> Any:
    response = httpx.get(f"{API_URL}{path}", timeout=30)
    response.raise_for_status()
    body = response.json()
    if body.get("job_id") and body.get("status"):
        return body
    if not body.get("ok", False):
        error = body.get("error") or {}
        raise ApiError(error.get("message", "API request failed"))
    return body["data"]


def api_post(path: str, payload: dict[str, Any]) -> Any:
    response = httpx.post(f"{API_URL}{path}", json=payload, timeout=30)
    response.raise_for_status()
    body = response.json()
    if body.get("job_id") and body.get("status"):
        return body
    if not body.get("ok", False):
        error = body.get("error") or {}
        raise ApiError(error.get("message", "API request failed"))
    return body["data"]


def render_chart(chart_json: str, key: str) -> None:
    st.plotly_chart(pio.from_json(chart_json), use_container_width=True, key=key)


def not_seeded_warning(symbol: str) -> None:
    st.warning(
        f"No cached data for **{symbol}**. Run `./dev_start.sh` or "
        f"`uv run python -m scripts.seed_universe --symbols {symbol}` to fetch it."
    )


def poll_job(job_id: str) -> Any:
    progress = st.progress(0, text="Queued...")
    with st.status("Running backend job", expanded=False) as status:
        for _ in range(120):
            job = api_get(f"/api/v1/jobs/{job_id}")
            pct = min(max(job.get("progress_pct") or 0, 0), 100)
            progress.progress(pct, text=job["status"])
            if job["status"] == "succeeded":
                status.update(label="Job complete", state="complete")
                return api_get(f"/api/v1/jobs/{job_id}/result")
            if job["status"] == "failed":
                status.update(label="Job failed", state="error")
                st.error(job.get("error") or "Backend job failed")
                return None
            time.sleep(1)
        status.update(label="Job timed out", state="error")
        st.error("Backend job timed out — check that the Celery worker is running.")
    return None


# ---------------------------------------------------------------------------
# Sidebar: symbol picker
# ---------------------------------------------------------------------------


@st.cache_data(ttl=5, show_spinner=False)
def fetch_symbols() -> list[dict[str, Any]]:
    return api_get("/api/v1/market/symbols")


@st.cache_data(ttl=60, show_spinner=False)
def fetch_strategies() -> list[str]:
    return api_get("/api/v1/market/strategies")


def choose_symbol() -> str | None:
    try:
        symbols = fetch_symbols()
    except (httpx.HTTPError, ApiError):
        return None
    cached = [s for s in symbols if s.get("cached")]
    if not cached:
        st.sidebar.warning("No symbols seeded yet. Run the seed script first.")
        return None
    labels = [f"{s['symbol']}  ({s.get('name', '?')})" for s in cached]
    default = 0
    for i, s in enumerate(cached):
        if s["symbol"] == "^NSEI":
            default = i
    label = st.sidebar.selectbox("Symbol (seeded)", labels, index=default)
    return cached[labels.index(label)]["symbol"]


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def home_page() -> None:
    st.title("Indian Portfolio Intelligence")
    st.markdown(
        "Regime-aware, risk-adjusted, overfitting-controlled strategy evaluation "
        "for Indian equities."
    )
    st.caption("BCS685 Major Project — K.S. Institute of Technology, batch 2026_CSE_01")

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("The Problem")
        st.markdown(
            "- **93%** of individual F&O traders lost money FY22-FY24 (SEBI).\n"
            "- Aggregate losses of ~₹1.8 lakh crore.\n"
            "- SEBI's prescribed remedy: *improved financial education and "
            "investor awareness.*\n\n"
            "This platform **is** that education layer: it shows *which* strategy "
            "suits *which* market regime, and tells you whether a backtest is "
            "trustworthy — instead of a pretty but overfit equity curve."
        )
    with col_b:
        st.subheader("The Solution")
        st.markdown(
            "- **Regime detection** (HMM): identifies bull / bear / sideways markets.\n"
            "- **5 strategies** backtested with real Indian transaction costs.\n"
            "- **Risk analytics**: volatility, VaR, Expected Shortfall, drawdown.\n"
            "- **Recommendation engine**: matches strategy to current regime.\n"
            "- **Trust layer** (Iteration 2): PBO, Deflated Sharpe, walk-forward validation."
        )

    st.divider()
    st.subheader("Machine Learning in Iteration 1")
    st.markdown(
        "| Component | Method |\n"
        "|---|---|\n"
        "| Regime detection | **Gaussian HMM** (3 states: bull, bear, sideways) |\n"
        "| Baselines | K-means, Wasserstein K-means |\n"
        "| Validation | Davies-Bouldin, Dunn index, MMD, transition matrix |\n"
        "| Features | RSI, MACD, ATR, moving averages, momentum, EWMA volatility |\n"
        "| Recommendation | Rule-based regime→strategy suitability matrix |\n"
    )
    st.info(
        "**Iteration 2 ML:** Random Forest regime prediction (SHAP), walk-forward / "
        "CPCV validation, PBO & Deflated Sharpe, GARCH volatility, VAE stress testing, "
        "LSTM-DNN prediction demo (base-paper honor, framed as 'prediction alone is "
        "insufficient')."
    )

    st.divider()
    st.subheader("Tech Stack")
    tech_cols = st.columns(4)
    tech_cols[0].markdown(
        "**Backend**\n- FastAPI\n- Celery + Redis\n- Postgres\n- Python 3.11 / uv"
    )
    tech_cols[1].markdown(
        "**Data**\n- yfinance + nsepython\n- Parquet cache\n- pandas + ta\n- pyarrow"
    )
    tech_cols[2].markdown(
        "**ML / Quant**\n- hmmlearn\n- scikit-learn\n- vectorbt\n- scipy / statsmodels"
    )
    tech_cols[3].markdown("**Frontend**\n- Streamlit\n- Plotly\n- httpx\n- Docker Compose")

    st.divider()
    st.subheader("How to Use This App")
    st.markdown(
        "1. **Market** — view adjusted price history for seeded symbols.\n"
        "2. **Backtest** — run a strategy or compare all 5; see equity, drawdown, trades.\n"
        "3. **Regime** — HMM bull/bear/sideways overlay on price + validation metrics.\n"
        "4. **Risk** — volatility, VaR, Expected Shortfall, max drawdown.\n"
        "5. **Recommend** — current regime → suggested strategy + suitability scores.\n"
    )
    st.warning("Not investment advice. This is an educational research platform.")


def market_page(symbol: str) -> None:
    st.header("Market Data")
    st.caption(f"Symbol: `{symbol}` — adjusted daily OHLCV from parquet cache.")
    try:
        records = api_get(f"/api/v1/market/{symbol}/series")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            not_seeded_warning(symbol)
            return
        st.error(str(exc))
        return
    if not records:
        not_seeded_warning(symbol)
        return

    latest = records[-1]
    col1, col2, col3 = st.columns(3)
    col1.metric("Latest close", f"{latest.get('close', 0):,.2f}")
    col2.metric("Observations", f"{len(records):,}")
    col3.metric("Date range", f"{records[0].get('date', '?')} → {latest.get('date', '?')}")

    try:
        chart = api_get(f"/api/v1/report/{symbol}/equity")
        render_chart(chart, "market-price")
    except (httpx.HTTPError, ApiError) as exc:
        st.error(f"Chart unavailable: {exc}")


STRATEGY_INFO = {
    "buy_and_hold": "Passive benchmark — buy and hold the asset throughout.",
    "ma_crossover": "Fast/slow moving-average crossover (default 20/50).",
    "rsi": "Relative Strength Index overbought/oversold reversal.",
    "momentum": "Momentum-based trend following (60-day lookback).",
    "mean_reversion": "Z-score mean reversion around the 20-day mean.",
}


def backtest_page(symbol: str, strategies: list[str]) -> None:
    st.header("Backtest")
    st.caption(f"Symbol: `{symbol}` — vectorbt engine, net of Indian transaction costs.")

    strategy = st.selectbox(
        "Strategy",
        strategies,
        format_func=lambda s: f"{s} — {STRATEGY_INFO.get(s, '')}",
    )
    show_costs = st.checkbox(
        "Net of Indian transaction costs (STT, brokerage, slippage)",
        value=True,
        help="Toggle to compare gross vs net-of-costs returns.",
    )

    col_run, col_compare = st.columns(2)
    with col_run:
        if st.button("Run Single Backtest", type="primary"):
            _run_single_backtest(symbol, strategy, show_costs)
    with col_compare:
        if st.button("Compare All Strategies"):
            _run_compare(symbol, strategies, show_costs)


def _run_single_backtest(symbol: str, strategy: str, net_of_costs: bool) -> None:
    try:
        job = api_post(
            "/api/v1/backtest",
            {"symbol": symbol, "strategy": strategy, "net_of_costs": net_of_costs},
        )
    except (httpx.HTTPError, ApiError) as exc:
        st.error(f"Submit failed: {exc}")
        return
    result = poll_job(job["job_id"])
    if not result:
        return
    try:
        charts = api_post("/api/v1/report/backtest", result)
        st.subheader("Equity vs Benchmark")
        render_chart(charts["equity"], "backtest-equity")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Drawdown")
            render_chart(charts["drawdown"], "backtest-drawdown")
        with col2:
            st.subheader("Trade Outcomes")
            render_chart(charts["trades"], "backtest-trades")
        st.subheader("Performance Metrics")
        st.dataframe(result["metrics"], use_container_width=True)
    except (httpx.HTTPError, ApiError) as exc:
        st.error(f"Chart render failed: {exc}")


def _run_compare(symbol: str, strategies: list[str], net_of_costs: bool) -> None:
    try:
        job = api_post(
            "/api/v1/backtest/compare",
            {"symbol": symbol, "strategies": strategies, "net_of_costs": net_of_costs},
        )
    except (httpx.HTTPError, ApiError) as exc:
        st.error(f"Submit failed: {exc}")
        return
    result = poll_job(job["job_id"])
    if not result:
        return
    try:
        st.subheader("Strategy Comparison")
        render_chart(api_post("/api/v1/report/compare", result), "strategy-comparison")
        if result.get("results"):
            st.subheader("Metrics Summary")
            rows = [r["metrics"] for r in result["results"]]
            st.dataframe(rows, use_container_width=True)
    except (httpx.HTTPError, ApiError) as exc:
        st.error(f"Chart render failed: {exc}")


def regime_page(symbol: str) -> None:
    st.header("Market Regime (HMM)")
    st.caption(
        f"Symbol: `{symbol}` — 3-state Gaussian HMM (bull / sideways / bear). "
        "Coloured bands show detected regimes on the price chart."
    )
    try:
        regime = api_get(f"/api/v1/regime/{symbol}/timeline")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            not_seeded_warning(symbol)
            return
        st.error(str(exc))
        return

    labels = regime["labels"]
    state_names = regime["state_names"]
    current = state_names.get(str(labels[-1]), "unknown")
    st.metric("Current regime", current.title())

    try:
        chart = api_get(f"/api/v1/report/{symbol}/equity")
        render_chart(chart, "regime-price")
    except (httpx.HTTPError, ApiError) as exc:
        st.error(f"Chart unavailable: {exc}")

    with st.expander("Validation metrics (HMM vs baselines)"):
        st.json(regime.get("validation"))


def risk_page(symbol: str) -> None:
    st.header("Risk Analytics")
    st.caption(f"Symbol: `{symbol}` — EWMA volatility, VaR, Expected Shortfall (1-day horizon).")
    try:
        risk = api_get(f"/api/v1/risk/{symbol}")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            not_seeded_warning(symbol)
            return
        st.error(str(exc))
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("EWMA volatility", f"{risk['annualized_vol_pct']:.2f}%")
    col2.metric("VaR 95%", f"{risk['var_95_pct']:.2f}%")
    col3.metric("Expected shortfall", f"{risk['expected_shortfall_95_pct']:.2f}%")
    col4.metric("Max drawdown", f"{risk['max_drawdown_pct']:.2f}%")

    with st.expander("Full risk report"):
        st.json(risk)


def recommend_page(symbol: str) -> None:
    st.header("Strategy Recommendation")
    st.caption(f"Symbol: `{symbol}` — regime-aware suitability scoring, rule-based v1.")
    try:
        rec = api_get(f"/api/v1/recommend/{symbol}")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            not_seeded_warning(symbol)
            return
        st.error(str(exc))
        return

    regime = rec.get("current_regime", {})
    col1, col2 = st.columns(2)
    col1.metric("Current regime", str(regime.get("state_name", "?")).title())
    col2.metric("Suggested strategy", rec["suggested_strategy"])

    st.subheader("Suitability scores")
    try:
        render_chart(api_post("/api/v1/report/suitability", rec), "suitability")
    except (httpx.HTTPError, ApiError) as exc:
        st.error(f"Chart unavailable: {exc}")

    st.subheader("Rationale")
    for reason in rec.get("rationale", []):
        st.markdown(f"- {reason}")

    st.warning(rec.get("caveat", "Not investment advice."))


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

PAGES = ["Home", "Market", "Backtest", "Regime", "Risk", "Recommend"]

try:
    page = st.sidebar.radio("Navigation", PAGES, label_visibility="collapsed")
    symbol = None
    if page != "Home":
        symbol = choose_symbol()

    if page == "Home":
        home_page()
    elif page == "Market":
        if symbol:
            market_page(symbol)
    elif page == "Backtest":
        if symbol:
            strategies = fetch_strategies()
            backtest_page(symbol, strategies)
    elif page == "Regime":
        if symbol:
            regime_page(symbol)
    elif page == "Risk":
        if symbol:
            risk_page(symbol)
    elif page == "Recommend":
        if symbol:
            recommend_page(symbol)
except (httpx.HTTPError, ApiError, KeyError, ValueError) as exc:
    st.error(f"Cannot reach portfolio API at {API_URL}: {exc}")
    st.info("Start the backend with `./dev_start.sh` or `make api`.")

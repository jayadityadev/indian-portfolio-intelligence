# Implementation Plan — Indian Market Portfolio Intelligence & Backtesting Platform

> **Project:** Indian Market Portfolio Intelligence & Backtesting Platform (BCS685 Phase-I / Phase-II)
> **Team:** Jayaditya Dev · Durgashree M · Aryaman Tiwari · Chirag T · Guide: Mrs. Beena K
> **Base paper:** "Enhancing Stock Market Prediction: A Robust LSTM-DNN Model..." (Alam et al., IEEE Access 2024)
> **Version:** 1.0 · **Status:** Locked (vetted via design grill, external-API research, and SEBI problem validation)

---

## 0. Document Purpose

This is the single source of truth for *how* we build the platform. It locks:

1. The product thesis and the problem we are solving (with regulator evidence).
2. Every technology decision and the reasoning behind it.
3. The architecture (module maps, ML pipeline, deployment) as mermaid diagrams.
4. The monorepo layout and Git workflow.
5. **The data + API contracts** that make integration between teammates safe.
6. Two iteration work-packages with per-teammate tasks, acceptance criteria, and integration notes.
7. Quality gates, risks, and the demo script.

Read §10 (contracts) before writing any code. Follow §7 (Git) from commit #1.

---

## 1. Product Summary & Thesis

**One-liner:** *The base paper stops at "predicting price". We prove that prediction alone is insufficient and build the missing layer — a regime-aware, risk-adjusted, overfitting-controlled strategy-evaluation platform for Indian retail investors.*

| Module | What it does | Technique |
|---|---|---|
| M1 — Market Regime Detection | Classify market state (bull / bear / sideways) over time | Gaussian HMM (detection) + Random Forest (ex-ante prediction); k-means / Wasserstein k-means as baselines |
| M2 — Strategy Evaluation & Suitability | Backtest 5 strategies, score which strategy fits the current regime | vectorbt engine + performance metrics + suitability recommender |
| M3 — Risk Forecasting | Forecast volatility & tail risk, quantify drawdowns | EWMA / GARCH vol, VaR, Expected Shortfall; (iter-2: VAE stress testing) |

**Strategy universe (M2):** Buy & Hold, Moving Average Crossover, RSI mean-reversion, Momentum, Mean Reversion.

**Data universe:** NIFTY-50 index + constituents, ~20 years of daily OHLCV, split/dividend-adjusted.

**Target user:** Indian retail investor who currently trades with gut feel and loses money (see §2).

**Differentiator (our answer to "why not just another backtester?"):**
- Portfolio-level (multi-symbol) backtesting, not single-symbol indicator rules.
- Regime-aware recommendation — the engine tells you *which* strategy suits *this* market, not just how a strategy performed in the past.
- A **rigor/trust layer**: walk-forward + Combinatorial Purged CV (CPCV), Probability of Backtest Overfitting (PBO), Deflated Sharpe Ratio (DSR), transaction-cost netting. This is what papers #11 and #12 demand and what Streak/Sensibull/TradingView do *not* provide.
- Retail-Indian-native: NSE symbols, ₹ costs, Indian index universe.

---

## 2. Problem Validation (Regulator Evidence)

SEBI's own studies justify the project. Quote directly in the report's "Problem Identification" chapter.

| Stat | Source |
|---|---|
| 93% of individual F&O traders lost money in FY22–FY24 | SEBI updated study, Sep 2024 |
| 89% of individual equity F&O traders lost money in FY22 | SEBI study, Jan 2023 |
| Aggregate retail losses exceeded **₹1.8 lakh crore (~US$21B)** over 3 years (~₹2L avg loss/trader) | SEBI Sep 2024 |
| 75% of loss-making traders continued trading despite consecutive losses | SEBI Sep 2024 |
| Young traders (<30) grew from 31% → 43% of F&O participants | SEBI Sep 2024 |
| SEBI's stated remedy: "improved financial education and investor awareness" | SEBI Sep 2024 |

**Conclusion:** We are building the education + awareness tool the regulator says is missing. This is the strongest possible justification for a "contribution to society" chapter.

---

## 3. Goals & Non-Goals

### Goals
- A working, demoable end-to-end platform after Iteration 1 (~60% of total effort).
- Backtest results that are *trustworthy* (walk-forward + PBO + DSR), not just pretty equity curves.
- Clean module boundaries so 4 people can integrate without stepping on each other.
- Free hosting: frontend on Vercel, backend on an always-free cloud VM.
- Professional-looking charts (TradingView Charting Library) by Iteration 2.

### Non-Goals (explicitly out of scope)
- Live/paper trading execution (no broker integration; Kite/Upstox explicitly skipped).
- Intraday/minute data. Daily only.
- Real-time streaming. Batch/daily cadence only.
- Options/F&O backtesting. Cash-equity strategies only.
- Production-grade multi-tenancy / auth (single demo user; `users` table reserved for future).
- Microservices/kubernetes/service mesh. We are a **modular monolith in containers** — 5 containers max.

---

## 4. Tech Stack & Decision Log

Every decision below was made deliberately. If you want to change one, say why in a PR description — do not silently swap.

| # | Decision | Choice | Why / rationale |
|---|---|---|---|
| D1 | Language | Python 3.11 | Ecosystem for quant/ML. Single language across data/backtest/API. |
| D2 | API framework | FastAPI + Pydantic v2 | Async, auto OpenAPI docs, typed request/response = integration contract for free. |
| D3 | Async job execution | Celery + Redis | Backtests/ML runs are minutes-long; keep HTTP fast, queue work to worker. |
| D4 | Backtest engine | vectorbt (primary) | Vectorized, fast, native portfolio-level multi-symbol + rebalancing. |
| D5 | Backtest engine fallback | backtrader | Only for stateful/path-dependent strategies that vectorbt cannot express cleanly. |
| D6 | Regime detection | Gaussian HMM (`hmmlearn`) | SOTA regime segmentation (Wang #10). 3 states: bull/bear/sideways. |
| D7 | Regime prediction (ex-ante) | Random Forest (KMRF-style, #11) | HMM detects *after* onset; RF predicts *before*. Needed for recommendations. |
| D8 | Regime baselines | k-means, Wasserstein k-means (#9) | Mandatory comparison so we can *show* HMM is better. |
| D9 | Indicators | `ta` library + manual pandas | Maintained, pure-Python, no numba. (Note: `pandas-ta` was dropped — it now demands Python ≥3.12 and is abandoned.) |
| D10 | Volatility | `statsmodels` GARCH + EWMA | GARCH for iter-2 forecasts; EWMA for iter-1. |
| D11 | LSTM-DNN demo | Keras (tf) | Lightweight; honors base paper; **demo-only, never a signal source**. |
| D12 | Primary data source | `yfinance` `.NS` / `.BO`, `auto_adjust=True` | Free, no auth, 20yr adjusted history, most reliable free source. |
| D13 | Data fallback | `nsepython` (server edition) | NSE-native REST, fundamentals; newer + maintained (v2.97, May 2025). `nsepy` is abandoned. |
| D14 | Data cross-check | Twelve Data (optional) | Free 800 req/day, `.NSE` support — third source for spot-checks only. |
| D15 | Time-series storage | Parquet files (pyarrow) + manifest | Columnar, fast, zero-ops. Never re-fetch on request. |
| D16 | Metadata DB | PostgreSQL | Symbols, jobs, results, strategy defs, users. |
| D17 | Charts (iter-1) | Plotly (server-rendered JSON) | Rich, interactive, free, Python-native. |
| D18 | Frontend (iter-1) | Streamlit | Dashboards in days; demoable immediately. |
| D19 | Frontend (iter-2) | Next.js (App Router) on Vercel | Product-grade story; server-side rendering. |
| D20 | Chart widget (iter-2) | TradingView Charting Library (free embed) | Pro-grade charts fed by **our own** data via Datafeed. TradingView has no public data API — UI only, never data. |
| D21 | Deployment | Backend: docker-compose on Oracle Cloud always-free VM (4 ARM cores / 24GB). Frontend: Vercel. | Free, no sleep penalty (Render sleeps). Vercel cannot run Python compute, so split is natural. |
| D22 | Dev environment | docker-compose (local) mirroring prod | "Works on my machine" is eliminated. |
| D23 | Architecture style | Modular monolith, monorepo | 4 people (effectively ~1.5 full-time devs); one codebase, clean boundaries, 5 containers. |
| D24 | Auth | None now; `users` table + JWT-ready endpoints reserved | College demo, single user. |

---

## 5. Architecture

### 5.1 System Context

```mermaid
flowchart LR
    User[Retail Investor] -->|HTTPS| FE[Vercel: Next.js frontend]
    FE -->|REST/JSON| API[FastAPI on VM]
    API -->|enqueue job| RQ[Redis queue]
    RQ --> W[Celery Worker]
    W -->|backtest / ML / report| PC[(Parquet store)]
    W --> PG[(PostgreSQL metadata)]
    API --> PG
    API --> PC
    W -->|fetch OHLCV| Y[yfinance .NS]
    W -->|fallback + fundamentals| N[nsepython]
    W -->|optional spot-check| T[Twelve Data]

    subgraph VM[Free Cloud VM - docker-compose]
        API
        RQ
        W
        PG
        PC
    end
```

### 5.2 Module Dependency (monorepo packages)

Dependency direction is **one-way downward** — a module may import modules below it, never above it. `api` is the only outward-facing layer.

```mermaid
flowchart TD
    data --> features
    features --> regime
    features --> backtest
    features --> risk
    data --> risk
    regime --> recommend
    backtest --> recommend
    risk --> recommend
    validation --> backtest
    validation --> recommend
    report --> backtest
    report --> regime
    report --> risk
    report --> recommend
    api --> data
    api --> regime
    api --> backtest
    api --> risk
    api --> recommend
    api --> validation
    api --> report
```

### 5.3 ML Pipeline (the spine)

```mermaid
flowchart TD
    OHLCV[OHLCV parquet] --> FE[Feature engineering]
    FE --> HMM[Gaussian HMM - regime detection]
    HMM --> RT[Regime timeline + viz]
    FE --> KM[K-means / Wasserstein k-means baselines]
    HMM --> RV[Regime validation: MMD / Davies-Bouldin / Dunn]
    FE --> RF[Random Forest - ex-ante regime prediction]
    RF --> SC[Suitability score]
    FE --> BT[vectorbt backtest - 5 strategies]
    BT --> MET[Performance metrics]
    SC --> REC[Recommendation: regime → strategy → confidence]
    MET --> REC
    FE --> LSTM[LSTM-DNN price prediction - DEMO ONLY]
    LSTM --> WD[Walk-forward validation, labeled 'insufficient alone']
    BT --> WF[Walk-forward + CPCV + PBO + DSR + tx-costs]
    WF --> TR[Backtest trust report]
    REC --> TR
```

### 5.4 Deployment

```mermaid
flowchart LR
    Dev[Local docker-compose] --> Git[GitHub]
    Git --> CI[GitHub Actions: lint + typecheck + tests]
    CI --> VM[Oracle free VM: docker-compose prod - api+worker+redis+postgres+parquet]
    CI --> VERCEL[Vercel: Next.js (iter-2) / Streamlit Community Cloud (iter-1 optional)]
```

---

## 6. Repository Layout (Monorepo)

```
indian-portfolio-intelligence/
├─ app/                         # Python package (the whole backend)
│  ├─ __init__.py
│  ├─ config.py                 # pydantic-settings; all env vars here
│  ├─ schemas.py                # SHARED data contracts (see §10) — read before coding
│  ├─ data/                     # ingestion + cache
│  │  ├─ sources.py             # yfinance / nsepython / twelvedata adapters
│  │  ├─ cache.py               # parquet read/write + manifest
│  │  ├─ adjust.py              # raw-vs-adjusted integrity validation
│  │  └─ universe.py            # symbol list (NIFTY-50 + index)
│  ├─ features/
│  │  ├─ indicators.py          # MA/RSI/Momentum/vol/returns/drawdown
│  │  └─ target.py              # labels for ML (forward returns, regime label windows)
│  ├─ regime/
│  │  ├─ hmm.py                 # Gaussian HMM detector (hmmlearn)
│  │  ├─ rf.py                  # ex-ante regime predictor (KMRF-style)
│  │  ├─ baselines.py           # k-means, Wasserstein k-means
│  │  └─ validate.py            # MMD / Davies-Bouldin / Dunn
│  ├─ backtest/
│  │  ├─ engine.py              # vectorbt wrapper → BacktestResult
│  │  ├─ strategies.py          # 5 strategy defs (see §12)
│  │  ├─ metrics.py             # CAGR/Sharpe/Sortino/MaxDD/vol/IR (see §13)
│  │  └─ portfolio.py           # multi-symbol rebalancing
│  ├─ risk/
│  │  ├─ volatility.py          # EWMA (iter-1), GARCH (iter-2)
│  │  ├─ var.py                 # VaR / Expected Shortfall (historical + parametric)
│  │  └─ stress.py              # iter-2: VAE stress testing (#7)
│  ├─ recommend/
│  │  ├─ scoring.py             # regime→strategy suitability matrix
│  │  └─ service.py             # assemble Recommendation
│  ├─ validation/
│  │  ├─ walk_forward.py        # time-series CV
│  │  ├─ cpcv.py                # Combinatorial Purged CV (#12)
│  │  ├─ pbo.py                 # Probability of Backtest Overfitting
│  │  ├─ dsr.py                 # Deflated Sharpe Ratio
│  │  └─ costs.py               # brokerage/stamp/STT/slippage netting
│  ├─ report/
│  │  ├─ charts.py              # Plotly figures (equity, regime timeline, heatmap)
│  │  └─ trust.py               # trust report builder
│  ├─ ml/
│  │  ├─ lstm_dnn.py            # demo prediction model (base-paper honor)
│  │  └─ artifacts.py           # model save/load + versioning
│  └─ api/
│     ├─ main.py                # FastAPI app, router mount
│     ├─ jobs.py                # job endpoints (submit/poll/results)
│     ├─ market.py              # symbol list, quotes, series
│     ├─ backtest.py            # backtest + results
│     ├─ regime.py              # regime timeline + current regime
│     ├─ risk.py                # risk metrics
│     ├─ recommend.py           # recommendation endpoint
│     └─ deps.py                # DB sessions, worker client
├─ frontend/                    # iter-1: streamlit_app.py ; iter-2: Next.js app
│  ├─ streamlit/                # iter-1
│  │  └─ app.py
│  └─ nextjs/                   # iter-2 (added in iteration 2)
├─ scripts/
│  ├─ seed_universe.py          # build parquet cache for NIFTY-50 (Chirag)
│  ├─ sync_daily.py             # daily incremental sync (cron)
│  └─ validate_data.py          # cross-source integrity check
├─ tests/                       # pytest; mirror app/ layout
│  ├─ unit/
│  ├─ integration/
│  └─ fixtures/                 # tiny parquet + csv fixtures (checked in)
├─ mlruns/                      # optional experiment tracking (local, gitignored)
├─ docker/
│  ├─ api.Dockerfile
│  ├─ worker.Dockerfile
│  └─ frontend.Dockerfile       # iter-1 streamlit image
├─ docker-compose.yml           # local + prod (env-file switch)
├─ pyproject.toml               # single source of truth for deps + tooling
├─ .env.example                 # all env vars documented
├─ .gitignore
├─ .github/workflows/ci.yml     # lint + typecheck + pytest
├─ Makefile                     # common commands (make dev, make test, make seed…)
├─ README.md
└─ docs/
   ├─ IMPLEMENTATION_PLAN.md    # this file
   ├─ Papers/  Report and PPT/  Existing Platforms.txt   (already present)
   └─ INTERFACES.md             # generated from schemas.py once live
```

---

## 7. Git Setup & Workflow

### 7.1 Repo bootstrap (done by Jayaditya on day 1)
1. `git init -b main`
2. Create the skeleton above (empty module dirs + `__init__.py`, `pyproject.toml`, `.env.example`, `docker-compose.yml`, `.gitignore`, `Makefile`, CI workflow).
3. First commit: "chore: scaffold monorepo skeleton". Tag `v0.1.0`.
4. Push to GitHub. Create teams: **Jayaditya** (maintainer), **Durgashree**, **Aryaman**, **Chirag**.
5. Protect `main`: require PR + 1 approval + CI green before merge. Branches only via feature branches.

### 7.2 Branching model (trunk-based, short-lived branches)
```mermaid
gitGraph
    commit id: "scaffold"
    commit id: "contracts"
    branch feat/data
    branch feat/regime
    branch feat/backtest
    branch feat/frontend
    commit id: "data srcs"
    commit id: "regime hmm"
    commit id: "engine"
    checkout main
    merge feat/data
    merge feat/regime
    merge feat/backtest
    branch feat/risk
    branch feat/recommend
    commit id: "risk var"
    commit id: "rec scoring"
    checkout main
    merge feat/risk
    merge feat/recommend
    merge feat/frontend
    commit id: "iter1 demo"
```

**Rules:**
- Branch name: `feat/<module>/<what>` or `fix/<module>/<what>` (e.g. `feat/backtest/costs`).
- Commit messages: **Conventional Commits** — `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`. Subject ≤ 50 chars. Body explains *why* only when non-obvious.
- Never commit to `main` directly. Always PR.
- One logical change per commit; stage intentionally (`git add <files>`, not `git add -A` blindly).
- **Never commit secrets, `.env`, or parquet caches.** `.env` → `.env.example` only. Data cache dir is gitignored.
- Daily integration: merge `main` into your feature branch at least every evening to avoid divergence.

### 7.3 CI gate (GitHub Actions, `ci.yml`)
On every PR and push to `main`:
1. `ruff check` (lint) — fail on errors.
2. `ruff format --check` (or black --check) — formatting.
3. `mypy app` (typecheck) — strict-ish on `app/`.
4. `pytest tests/unit` — must pass.
5. `pytest tests/integration -m "not slow"` — fast integration only (no network).
> Slow/network tests are marked `@pytest.mark.slow` and run nightly or on `v*` tags.

### 7.4 Milestone tags
- `v0.1.0` scaffold · `v0.2.0` data layer · `v0.3.0` features+regime · `v0.4.0` backtest+metrics · `v0.5.0` risk+recommend · `v1.0.0` **Iteration 1 complete (demo)** · `v2.0.0` **Iteration 2 complete (final)**.

---

## 8. Environment & Tooling

### 8.1 Python environment
- `uv` or `poetry` (pick one — **uv**, faster). `pyproject.toml` is the single source of truth.
- Lockfile (`uv.lock`) committed. Everyone uses the same exact deps.
- Python 3.11. `.python-version` pinned.

### 8.2 Docker compose (local = prod)
`docker-compose.yml` services: `api`, `worker`, `redis`, `postgres`, `frontend` (streamlit). Volume for parquet store. `.env` drives it (copy `.env.example` → `.env`).

### 8.3 Makefile commands
```make
make dev          # docker compose up (api+worker+redis+postgres+frontend)
make seed         # run scripts/seed_universe.py (fills parquet cache)
make test         # pytest
make lint         # ruff check
make typecheck    # mypy app
make sync         # run daily incremental sync
make down         # docker compose down
```

### 8.4 Env vars (`.env.example` — document every one)
```
POSTGRES_DSN=postgresql://ipu:ipu@postgres:5432/ipu
REDIS_URL=redis://redis:6379/0
PARQUET_DIR=/data/parquet
TWELVEDATA_API_KEY=            # optional, empty = disabled
NSEPYTHON_MODE=remote          # or 'server' with NSEPYTHON_SERVER
LOG_LEVEL=INFO
```

---

## 9. Data Layer Design

### 9.1 Sources
- **Primary:** `yfinance` — symbol convention `<SYMBOL>.NS` (NSE) / `.BO` (BSE), `auto_adjust=True` (split + dividend adjusted), `period="20y"`, `interval="1d"`. Index NIFTY-50 via `^NSEI`.
- **Fallback:** `nsepython` — NSE-native historical + fundamentals when Yahoo gaps or for corporate-action spot checks.
- **Cross-check (optional):** Twelve Data `<SYMBOL>.NSE`, used by `scripts/validate_data.py` only, never in the hot path.

### 9.2 Caching & integrity (the anti-corruption rule)
1. Backfill once via `scripts/seed_universe.py` → parquet per symbol under `PARQUET_DIR/<symbol>.parquet`.
2. A `manifest.json` (hash per symbol + last-updated + source + adjustment flag) lives beside the parquet files. If hash mismatches on read → treat cache as corrupt → re-seed that symbol.
3. **Never fetch on request.** API reads only parquet + Postgres. Worker performs fetch/sync.
4. **Adjustment validation** (`data/adjust.py`): for each symbol, fetch raw (auto_adjust=False) and adjusted; if a split/bonus occurred, raw-vs-adjusted ratio must jump exactly at the ex-date. Log any anomaly. **Unadjusted data silently corrupts backtests — this check is mandatory.**
5. Daily sync (`scripts/sync_daily.py`) appends new trading days only (check last parquet row date first), updates manifest.

### 9.3 Symbol universe
- NIFTY-50 index (`^NSEI`) + current NIFTY-50 constituents (~50) + optionally a small sector sample for iter-2 portfolio demo.
- Universe stored in Postgres `symbols` table (symbol, name, exchange, index_member bool, isin, sector). Seeded by `data/universe.py` (or from nsepython index constituents).

---

## 10. Shared Data Contracts — **READ BEFORE CODING** ⚠️

These are the integration backbone. Every module consumes/produces these shapes. Defined once in `app/schemas.py` (Pydantic). **Do not invent your own ad-hoc dicts.** If you need a new field, update the schema + this doc in the same PR.

### 10.1 MarketData (time-series)
```python
class MarketData(BaseModel):
    symbol: str
    source: Literal["yfinance", "nsepython", "twelvedata"]
    adjusted: bool                      # True = split/dividend adjusted
    freq: Literal["1d"]
    index: pd.DatetimeIndex             # tz-aware, exchange timezone (Asia/Kolkata), name "date"
    open, high, low, close, volume: pd.Series  # float64, NaN-tolerant
    # to_frame() returns DataFrame indexed by date with columns:
    #   ["open", "high", "low", "close", "volume"]
```
> Internal convention: time series flows as **pandas objects wrapped in small dataclasses**, but *every API/JSON boundary* converts to plain records (see 10.6). Tests use the pandas shapes.

### 10.2 FeaturesFrame
`pd.DataFrame` indexed by date, containing `close` plus at least:
```
returns_pct, log_return, vol_20 (rolling std), vol_ewma,
sma_20, sma_50, sma_200, ema_12, ema_26,
rsi_14, macd, macd_signal, momentum_20, momentum_60,
atr_14, max_drawdown_rolling, regime_label (int, optional - filled by regime module)
```

### 10.3 RegimeResult
```python
class RegimeResult(BaseModel):
    symbol: str
    method: Literal["hmm", "kmeans", "wkmeans"]
    n_states: int
    labels: list[int]                 # per-timestamp state id (0,1,2)
    state_names: dict[int, str]       # e.g. {0:"bull",1:"bear",2:"sideways"}
    log_likelihood: float | None      # HMM only
    validation: RegimeValidation       # see below
    fitted_at: datetime
```
```python
class RegimeValidation(BaseModel):
    davies_bouldin: float
    dunn_index: float
    mmd: float                        # distributional distance to baselines
    transition_matrix: list[list[float]] | None
```

### 10.4 BacktestResult
```python
class BacktestResult(BaseModel):
    symbol: str
    strategy: str                     # "buy_and_hold" | "ma_crossover" | "rsi" | "momentum" | "mean_reversion"
    params: dict                      # e.g. {"fast":20,"slow":50}
    start: date; end: date
    regime_method: str | None         # if backtest was regime-gated
    net_of_costs: bool
    metrics: PerformanceMetrics       # see 10.5
    equity_curve: list[EquityPoint]   # [{date, equity, benchmark}] (sampled: every point for demo, else max 2000 pts)
    trade_list: list[Trade]           # [{entry_date, exit_date, direction, pnl_pct, bars_held}]
    # for validation reports:
    trust: TrustReport | None         # filled by validation module
```

### 10.5 PerformanceMetrics (single canonical dictionary of metrics — §13)
```python
class PerformanceMetrics(BaseModel):
    cagr: float; total_return_pct: float
    sharpe: float; sortino: float; calmar: float; information_ratio: float
    max_drawdown_pct: float
    annualized_vol_pct: float
    win_rate_pct: float; profit_factor: float; avg_win_pct: float; avg_loss_pct: float
    num_trades: int; exposure_pct: float
    benchmark_return_pct: float; alpha_pct: float; beta: float
```

### 10.6 JSON boundary convention (API ↔ frontend)
- All dates as ISO `YYYY-MM-DD`. All series serialized as `[{ "date": "...", "value": 123.4 }, ...]`.
- All floats round-trippable; never serialize NaN (convert to `null`).
- Every endpoint returns `{"ok": true, "data": ...}` or `{"ok": false, "error": {"code": "...", "message": "..."}}`.

### 10.7 Job API
```python
class JobStatus(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    progress_pct: int | None
    result_ref: str | None            # path/key of result artifact
    error: str | None
```

---

## 11. Module Design Notes (per package)

### `data`
- Adapters implement one interface: `fetch(symbol, start, end) -> MarketData`. Source chosen by config + availability. Add nsepython/twelvedata behind the same interface — no other module knows the source.
- `cache.py` implements `load(symbol) -> MarketData` and `store(md)` with manifest handling.

### `features`
- `indicators.py`: pure functions `DataFrame -> DataFrame` (no I/O). Unit-testable with fixture parquet.
- `target.py`: label builders — forward return bins (for RF), regime label windows (no lookahead! see §14).

### `regime`
- `hmm.py`: `fit_hmm(features) -> RegimeResult`; state assignment resolved so labels are stable (state 0 = lowest mean return = bear, 2 = highest = bull by convention — document in code).
- `rf.py`: `train_rf(features, regime_labels) -> model` (predict regime *t+1* from features up to *t*); `predict_regime(model, features) -> array`.
- `baselines.py`, `validate.py`: metric functions producing `RegimeValidation`.

### `backtest`
- `engine.py`: `run(symbol, strategy, params, features, costs) -> BacktestResult`. Wraps vectorbt; if a strategy can't vectorize, fall back to backtrader (flag in result).
- `strategies.py`: declarative strategy defs (entry/exit functions over `FeaturesFrame`). See §12.
- `portfolio.py`: iter-2 multi-symbol equal-weight rebalance at N-day frequency; reuses `engine.py` per symbol.
- `metrics.py`: computes every field in `PerformanceMetrics` from equity curve + trade list. **Single implementation, used everywhere** (no duplicated metric math anywhere in the repo).

### `risk`
- `volatility.py`: EWMA vol (iter-1); GARCH(1,1) forecast (iter-2).
- `var.py`: historical VaR 95/99, ES, parametric VaR; horizon 1-day.
- `stress.py` (iter-2): VAE (papers #7) — synthetic stress scenarios, portfolio-level.

### `recommend`
- `scoring.py`: suitability matrix — for each (regime_state → strategy) an expected-suitability weight built from *validated* backtest results (iter-1: rule-based + simple RF; iter-2: RF-driven). 
- `service.py`: `recommend(symbol) -> Recommendation` where
```python
class Recommendation(BaseModel):
    symbol: str
    current_regime: dict              # state_name, confidence
    suggested_strategy: str
    rationale: list[str]              # human-readable, educational tone
    suitability: dict[str, float]     # score per strategy
    caveat: str                       # always a "not investment advice" line
```

### `validation`
- `walk_forward.py`: expanding/rolling origin CV; returns out-of-sample per-fold metrics.
- `cpcv.py`: CPCV per Arian et al. (#12); purging + embargo gap (no leakage, see §14).
- `pbo.py`: from CPCV path distribution → PBO (probability log-returns ratio < 0 over configs).
- `dsr.py`: Deflated Sharpe Ratio (Bailey & López de Prado) with expected max Sharpe under trial count.
- `costs.py`: Indian costs — brokerage (e.g. 0.03% per side), STT (0.1% delivery), stamp, exchange txn charge, slippage 0.05%. Configurable; **net-of-costs is the default** in results.

### `report`
- `charts.py`: Plotly figures → JSON for frontend: price+regime-shaded timeline, equity curve vs benchmark, drawdown, per-strategy metric comparison bars, suitability heatmap, trade scatter.
- `trust.py`: human-readable trust summary (PBO, DSR, folds, caveats).

### `ml`
- `lstm_dnn.py`: small Keras model, `predict_next_close` demo endpoint. **Every output carries a banner: "Research/diagnostic only. Prediction alone is insufficient — see evaluation layer."**
- `artifacts.py`: versioned model saves (`mlruns/<model>/<version>/`), load-on-demand.

### `api`
- Thin orchestration. Endpoints call services, return `schemas`, and for long jobs enqueue to Celery and return `JobStatus`. See §15 for the endpoint table.

---

## 12. Strategy Specifications (canonical)

Implemented in `backtest/strategies.py`. All entries/exits evaluated on **close**, signals computed from `FeaturesFrame` with **no lookahead** (signal at *t* uses data ≤ *t*).

| # | Strategy | Entry | Exit | Default params |
|---|---|---|---|---|
| 1 | `buy_and_hold` | day 1 | end | — |
| 2 | `ma_crossover` | sma_fast crosses above sma_slow | crosses below | fast=20, slow=50 (also 50/200 variant) |
| 3 | `rsi` | RSI(14) < 30 (oversold) | RSI(14) > 70 or after N bars | n=14, oversold=30, overbought=70 |
| 4 | `momentum` | 12-1 momentum rank / price above sma_200 & momentum > 0 | momentum < 0 or below sma_200 | lookback=120, hold=20 |
| 5 | `mean_reversion` | z-score(price, lookback) < -2 | z-score > 0 | lookback=20, entry_z=-2, exit_z=0 |

Regime-gating (iter-2): a strategy may be restricted to regimes where its suitability is positive (e.g. RSI in sideways, momentum in bull). Implemented as a filter on entry signals — never changes the strategy itself.

---

## 13. Metrics Dictionary (canonical definitions)

Computed by `backtest/metrics.py`. Use these exact formulas everywhere; add to this table if you add a metric.

| Metric | Definition |
|---|---|
| CAGR | (final/initial)^(1/years) − 1, annualized on calendar days |
| Total return | (final − initial)/initial × 100 |
| Annualized vol | std(daily returns) × √252 × 100 |
| Sharpe | (mean daily ret − rf_daily) / std(daily ret) × √252  (rf = 0 by default) |
| Sortino | (mean daily ret − rf) / downside std × √252 |
| Calmar | CAGR / |max drawdown| |
| Max drawdown | max peak-to-trough decline in equity, % |
| Information ratio | (strategy ann. ret − benchmark ann. ret) / tracking error |
| Win rate | winning trades / total trades × 100 |
| Profit factor | gross profit / gross loss |
| Alpha/Beta | OLS of strategy excess vs benchmark excess |
| Exposure | % of trading days with a position |

---

## 14. ML Methodology & Anti-Overfitting Rules (non-negotiable)

These rules are the *credibility* of the project. Violating one invalidates a result.

1. **No lookahead / leakage.** Features at *t* use data ≤ *t*. Labels for regime at *t* are built from the *same window* (HMM is causal-fit on a training window; never fit HMM on the test window).
2. **Train/test split is time-ordered always.** Random shuffles are forbidden for any time series model.
3. **Walk-forward everywhere.** Any claim ("strategy X works") must come from walk-forward or CPCV out-of-sample folds, not in-sample.
4. **Purge + embargo.** Between train and test folds, purge overlapping samples and add an embargo gap (≥ max label horizon) — required for CPCV.
5. **Multiple-testing guard.** When we try many (strategy × params × symbol), report PBO and Deflated Sharpe, not raw best Sharpe.
6. **Cost netting is default.** Results shown with costs. Never show gross-only as the headline.
7. **Regime validation.** HMM is compared against k-means and Wasserstein k-means via Davies-Bouldin, Dunn, MMD. If HMM is not better on these, say so honestly — that is still a valid, interesting result.
8. **LSTM-DNN is demo-only.** It is walk-forward validated and explicitly labeled insufficient; it must never feed the recommendation.

---

## 15. API Contract (endpoint table)

All under `/api/v1`. OpenAPI auto-generated by FastAPI.

| Method | Path | Purpose | Returns |
|---|---|---|---|
| GET | `/health` | liveness | `{ok, version}` |
| GET | `/market/symbols` | universe list | `[symbol, name, sector, index_member]` |
| GET | `/market/{symbol}/series` | OHLCV from parquet cache | records array |
| POST | `/backtest` | submit backtest job | `JobStatus` |
| GET | `/jobs/{job_id}` | poll job | `JobStatus` |
| GET | `/jobs/{job_id}/result` | fetch result | `BacktestResult` |
| POST | `/backtest/compare` | run N strategies vs benchmark | job → `CompareReport` (list of `BacktestResult`) |
| GET | `/regime/{symbol}/timeline` | regime labels + state_names | `RegimeResult` (+ series for shading) |
| GET | `/risk/{symbol}` | vol, VaR, ES, drawdown | `RiskReport` |
| GET | `/recommend/{symbol}` | current recommendation | `Recommendation` |
| GET | `/validation/{job_id}` | trust report for a backtest | `TrustReport` |
| POST | `/ml/predict-next` | LSTM-DNN demo | `{prediction, caveat}` |
| GET | `/report/{symbol}/equity` | Plotly JSON equity+drawdown+regime | Plotly JSON |

---

## 16. Frontend Plan

### Iter-1 (Streamlit, `frontend/streamlit/app.py`)
Pages (sidebar nav):
1. **Market**: symbol picker + price chart (Plotly) + quick stats.
2. **Backtest**: pick symbol, strategy, params → submit job → poll → show equity vs benchmark, metrics table, drawdown.
3. **Regime**: regime timeline shaded on price; current regime + confidence.
4. **Risk**: vol, VaR, ES, drawdown panel.
5. **Recommend**: current regime → suggested strategy + suitability bars + rationale.
- Calls the FastAPI JSON endpoints (10.6). Polls jobs with `st.status`/progress.
- **Streamlit is a thin client.** No business logic in the frontend, ever.

### Iter-2 (Next.js on Vercel)
- Pages mirror iter-1. Replace Plotly with **TradingView Charting Library** widget fed by our own Datafeed (wraps `/market/{symbol}/series` + `/regime/{symbol}/timeline` for shading).
- SSG for landing/about; CSR for data pages; API routes proxy `/api/v1` to the VM (CORS configured).
- Report export: downloadable PDF/HTML trust report.

---

## 17. Iteration 1 — Work Package (≈60% effort)

> **Per-teammate task lists now live in [`docs/team/`](team/README.md)** — one file
> per person with their exact tasks, owned files, and integration rules. This
> section keeps the consolidated iteration plan; read your own team file for the
> actionable version.

Goal: **a working end-to-end demo** (symbol → backtest → regime overlay → metrics → recommendation) running in docker-compose. Every task lists the owner, deliverable, and acceptance criteria.

> Effort split (internal, do not write into report): the architecture/ML-critical modules are owned by one lead so integration stays coherent.

### Iter-1 SPIKE (Jayaditya, first 3 days)
- [ ] Scaffold repo skeleton, pyproject, docker-compose, Makefile, CI (see §6–§8). Tag `v0.1.0`.
- [ ] Implement `schemas.py` (all of §10) + a `tests/unit/test_schemas.py`.
- [ ] Prove yfinance `.NS` backfill works for `^NSEI` + 5 symbols; validate `auto_adjust` split handling (`data/adjust.py`). Tag `v0.2.0`.
- **Done when:** `make dev` boots all 5 containers; `/health` returns `{ok:true}`; parquet cache for 5 symbols exists with manifest.

### T1 — Data layer (Chirag)
- [ ] Implement `scripts/seed_universe.py` for full NIFTY-50 + `^NSEI` using `data/sources.py` (yfinance primary, nsepython fallback).
- [ ] Implement `scripts/sync_daily.py` (incremental append + manifest update) and `scripts/validate_data.py` (Twelve Data spot-check, optional).
- [ ] Populate Postgres `symbols` table (name, sector, index_member, isin).
- **Acceptance:** `make seed` completes with zero source errors; manifest hashes consistent; `validate_data` passes for ≥20 symbols. 100% adjusted (`adjusted=True`).
- **Integration:** must consume and return `MarketData` (§10.1); never import other modules. Commit under `feat/data/...`.

### T2 — Features (Durgashree)
- [ ] `features/indicators.py`: implement every column in §10.2 (`ta` library or manual pandas — no I/O).
- [ ] `features/target.py`: forward-return bins + regime label windows (no lookahead).
- [ ] Unit tests against `tests/fixtures` parquet (tiny, checked-in).
- **Acceptance:** all columns of §10.2 present; NaN policy documented; tests green.
- **Integration:** pure functions `FeaturesFrame -> FeaturesFrame`; add new indicators in the same table §10.2 style. Commit under `feat/features/...`.

### T3 — Regime detection (Jayaditya)
- [ ] `regime/hmm.py` Gaussian HMM (3 states) + stable label convention (bear/bull/sideways by mean return).
- [ ] `regime/baselines.py` k-means + Wasserstein k-means; `regime/validate.py` (DB, Dunn, MMD).
- [ ] Expose via `/regime/{symbol}/timeline`.
- **Acceptance:** `RegimeResult` correct; comparison table HMM vs baselines non-trivial; tests green. Tag `v0.3.0` (with T2).
- **Integration:** consumes `FeaturesFrame`, returns `RegimeResult`. Durgashree's features must be column-compatible — coordinate once at kickoff.

### T4 — Backtest engine + metrics (Jayaditya)
- [ ] `backtest/strategies.py` (5 strategies, §12), `engine.py` (vectorbt, backtrader fallback), `metrics.py` (§13), `costs.py` (net-of-costs default).
- [ ] `/backtest` POST + job poll + result endpoints.
- **Acceptance:** each strategy returns `BacktestResult` with full metrics; net-vs-gross both computed; unit tests on known tiny fixture produce hand-checked numbers.
- **Integration:** define the exact strategy registry keys now (`buy_and_hold`, `ma_crossover`, `rsi`, `momentum`, `mean_reversion`) — frontend and recommend depend on these strings.

### T5 — Risk (Durgashree)
- [ ] `risk/volatility.py` EWMA; `risk/var.py` VaR/ES (historical + parametric); `/risk/{symbol}`.
- **Acceptance:** RiskReport matches hand-computed EWMA/VaR on fixture data within tolerance.
- **Integration:** consumes `FeaturesFrame`; returns metrics only — no plots (plots belong to `report`).

### T6 — Recommendation v1 (Jayaditya + Durgashree)
- [ ] `recommend/scoring.py` rule-based regime→strategy suitability matrix (literature + our backtest evidence), `service.py` assembles `Recommendation` with caveat.
- [ ] `/recommend/{symbol}`.
- **Acceptance:** recommendation changes with regime; rationale is educational; always includes "not investment advice" caveat.

### T7 — Report/charts (Aryaman)
- [ ] `report/charts.py`: Plotly JSON for equity+benchmark, drawdown, regime-shaded price, metric comparison, suitability bars, trade scatter.
- **Acceptance:** each chart is valid Plotly JSON consumable by Streamlit; NaN→null handled (§10.6).

### T8 — Frontend (Aryaman)
- [ ] `frontend/streamlit/app.py` with the 5 pages of §16.
- **Acceptance:** full demo path works against a running stack: pick symbol → run compare backtest → see regime overlay → risk panel → recommendation.
- **Integration:** consumes only API JSON; reads strategy registry keys from `/market` or a shared constant — no hardcoded drift.

### T9 — Demo + hardening (all)
- [ ] Write `docs/DEMO_SCRIPT.md` (see §23) and rehearse.
- [ ] Clean up: error messages, empty states, job failure handling.
- [ ] Tag `v1.0.0`. Screenshot every screen for the report.
- **Iteration 1 Done when:** demo runs from a fresh `git clone` + `make dev` + `make seed` on any laptop.

---

## 18. Iteration 2 — Work Package (≈40% effort)

Goal: **credibility layer + product polish + cloud deploy.** The differentiator lives here — do not treat it as optional.

### V1 — Validation layer (Jayaditya) ← the differentiator, schedule FIRST in iter-2
- [ ] `validation/walk_forward.py`, `cpcv.py` (purge+embargo), `pbo.py`, `dsr.py`, `costs.py` finalized.
- [ ] Wire `TrustReport` into `BacktestResult` and `/validation/{job_id}`.
- **Acceptance:** PBO/DSR computed on a config grid; leakage tests (see §14) enforced by test that asserts embargo gap.

### V2 — Regime RF predictor (Jayaditya)
- [ ] `regime/rf.py` KMRF-style ex-ante regime prediction + feature importances (SHAP/Boruta).
- [ ] Feed `Recommendation` confidence from RF (replaces rule-map confidence).
- **Acceptance:** RF predicts next-day regime out-of-sample with MCC + accuracy reported (dual eval per #11). Tag `v1.1.0`.

### V3 — VAE stress testing (Durgashree)
- [ ] `risk/stress.py` VAE on returns (paper #7), portfolio-level stress scenarios, VaR/ES under stress.
- **Acceptance:** stress VaR > historical VaR by construction; scenario narrative in report.

### V4 — Portfolio-level backtest + factor rotation (Jayaditya)
- [ ] `backtest/portfolio.py` equal-weight N-day rebalance; regime-rotation demo (paper #10 style).
- **Acceptance:** portfolio `BacktestResult` across ≥5 symbols; rotation vs static comparison.

### V5 — GARCH vol forecast (Durgashree)
- [ ] `risk/volatility.py` GARCH(1,1) 1- and 5-day vol forecast; into RiskReport.
- **Acceptance:** forecast within tolerance on fixture; documented stationary-test step.

### V6 — Next.js frontend + TradingView widget (Aryaman)
- [ ] `frontend/nextjs` app on Vercel; Datafeed wraps our API; Charting Library embed; report export.
- **Acceptance:** deploys from CI; all iter-1 pages reproduced with pro charts; CORS + env configured.

### V7 — Cloud deploy + hardening (Jayaditya + Chirag)
- [ ] Provision Oracle free VM; docker-compose prod; GitHub Actions deploy step; Vercel project; cron for `sync_daily`.
- [ ] Chirag: seed full universe on prod, verify `validate_data`, write ops notes.
- **Acceptance:** prod URL serves demo end-to-end; daily sync runs; 5 containers healthy.

### V8 — Report & documentation (Durgashree + Chirag)
- [ ] Full project report: methodology, SEBI problem chapter, results tables (with PBO/DSR), limitations, future work.
- [ ] README + architecture docs + `INTERFACES.md` regenerated.
- **Tag `v2.0.0`. Iteration 2 Done when:** everything deployable + documented + tested.

---

## 19. Teammate Integration Guidance (specific)

> **Moved to [`docs/team/`](team/README.md)** — one guide per teammate. The
> consolidated cross-cutting rules (daily main-merge, `[contracts]` PRs, single
> `metrics.py`, no-leakage) are reproduced there for each person. §19 below keeps
> only the ownership map for quick reference.

| Person | Owns | Consumes |
|---|---|---|
| Jayaditya | contracts, `data` adapters, `regime`, `backtest`, `validation`, `recommend`, `ml`, `api` | Durgashree's `features` |
| Durgashree | `features`, `risk`, report | frozen `FEATURE_COLUMNS` in `schemas.py` |
| Aryaman | `report` charts + frontend | API JSON only |
| Chirag | `scripts/*`, symbols seed, ops, slides | Jayaditya's `app/data` signatures |

Full per-person guidance: `docs/team/JAYADITYA.md`, `docs/team/DURGASHREE.md`,
`docs/team/ARYAMAN.md`, `docs/team/CHIRAG.md`.

### Jayaditya — backend core lead (data core, backtest, regime, validation, architecture)
- You own the contracts (`schemas.py`), the metrics implementation, and the anti-leakage tests. **Every module you ship must include the tests that prove it is correct** — teammates copy your test style.
- Coordinate schema changes: announce in #contracts channel/PR title `[contracts]`; merge contracts first, implementations second.
- Keep `metrics.py` the single implementation — reject duplicate metric math in review.
- Set the CI; enforce the git rules on every PR.

### Durgashree — features, risk, docs
- Features are consumed by *three* modules (regime, backtest, recommend) — the column names in §10.2 are a hard contract. Do not rename without a `[contracts]` PR.
- Risk module must be pure (inputs `FeaturesFrame`/returns → metrics). No charts, no API logic — Aryaman will visualize.
- Own the project report + methodology writing; pull numbers from validated results, never ad-hoc.

### Aryaman — frontend, charts, viz
- You are the only frontend owner. Backend teammates will *not* build UI. You consume only API JSON (§10.6) — if an endpoint shape is awkward, request a `[contracts]` change, don't parse around it.
- Keep the strategy registry keys (§17 T4) in a shared constant; import from the API, do not duplicate strings in the frontend.
- Plotly figures come from the backend as JSON — you render, you don't compute metrics in JS.

### Chirag — data pipeline scripts, ops, PPT/report support
- Your scripts are the *data quality gate*. A bad parquet cache silently corrupts every downstream module. The manifest + adjustment validation (§9.2) are yours to own and defend.
- You run `make seed` and `sync_daily` on prod; write the ops/runbook notes.
- Own PPT/slides and demo-run support; keep slides in sync with actual screenshots.

### Everyone — daily rules
- Pull `main` into your branch every evening; resolve conflicts immediately (they're usually in `schemas.py` or `pyproject.toml`).
- Write tests alongside code — CI fails without them (enforce with a coverage check on `app/` ≥ 70% in iter-1, ≥ 80% iter-2).
- No private ad-hoc naming. If it crosses a module boundary, it is a contract and goes through a `[contracts]` PR.

---

## 20. Risks & Mitigations

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | NSE data quality (gaps, unadjusted splits, delisted names) | Silent backtest corruption | Manifest hashes, raw-vs-adjusted validation (§9.2), nsepython fallback, Twelve Data spot-check |
| R2 | Scope creep toward microservices/k8s | Burnout, no demo | Modular monolith locked; 5 containers max; non-goals list enforced in review |
| R3 | Backtest overfitting → reviewers discount results | Project credibility | Walk-forward/CPCV/PBO/DSR as *default*, not feature; §14 rules enforced by tests |
| R4 | Team integration drift (naming, dict shapes) | Merge hell | `schemas.py` single source; `[contracts]` PR rule; daily main-merge |
| R5 | vectorbt can't express a strategy | Blocked module | backtrader fallback + strategy registry isolates the choice |
| R6 | HMM not better than baselines | Weak M1 story | Honest reporting is still valid; improve features or go k-means+RF only |
| R7 | Free VM instability / Oracle account issues | Deploy fails | Keep local demo as fallback; Vercel frontend independent of VM uptime |
| R8 | LSTM-DNN demoted to "useless" | Reviewer confusion | Frame explicitly: prediction-insufficiency IS the thesis (§1, §14.8) |

---

## 21. Milestones & Timeline

| Milestone | Contents | Tag | Target |
|---|---|---|---|
| M1 | Scaffold + contracts + data spike | v0.1.0–v0.2.0 | Week 1 |
| M2 | Features + regime + backtest + metrics working | v0.3.0–v0.4.0 | Week 2–3 |
| M3 | Risk + recommend + charts + Streamlit | v0.5.0 | Week 4 |
| M4 | **Iteration 1 demo complete** | **v1.0.0** | Week 5 |
| M5 | Validation layer (PBO/DSR) + RF predictor | v1.1.0 | Week 6–7 |
| M6 | VAE + GARCH + portfolio/rotation | v1.2.0 | Week 8 |
| M7 | Next.js + TradingView + cloud deploy | v1.3.0 | Week 9 |
| M8 | **Final: report + deploy + docs** | **v2.0.0** | Week 10 |

---

## 22. Definition of Done (every task/PR)

- [ ] Code passes `make lint`, `make typecheck`, `make test` locally and CI is green.
- [ ] Uses `schemas.py` shapes — no ad-hoc dicts at boundaries.
- [ ] Has unit tests (and integration tests where I/O involved, marked `slow`).
- [ ] No leakage: train/test time-ordered, purge+embargo where applicable.
- [ ] Numbers come from `metrics.py` (single implementation).
- [ ] API returns the `{ok, data/error}` envelope; NaN → null.
- [ ] Frontend consumes API JSON only.
- [ ] Docs updated if contracts or endpoints changed (`INTERFACES.md`).
- [ ] PR title/description: conventional, with `[contracts]` tag when `schemas.py` changes.

---

## 23. Demo Script (Iteration 1) — `docs/DEMO_SCRIPT.md` will contain

1. `git clone` → `make dev` → `make seed` (show parquet cache built).
2. Market page: NIFTY-50 20-year chart (adjusted).
3. Backtest: pick `ma_crossover` on `^NSEI` → submit → show job polling → equity vs benchmark + full metrics table + drawdown.
4. Compare tab: all 5 strategies side-by-side metrics.
5. Regime page: price shaded bull/bear/sideways; current regime + confidence; HMM vs k-means validation table.
6. Risk page: EWMA vol, VaR 95/99, ES, max drawdown.
7. Recommend page: current regime → suggested strategy + suitability bars + rationale + caveat.
8. LSTM-DNN demo: next-close prediction + the "insufficient alone" banner (honors base paper).
9. Close with the SEBI slide: "93% lose money — this tool is the education layer."
```
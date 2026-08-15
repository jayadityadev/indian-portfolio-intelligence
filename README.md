# Indian Portfolio Intelligence & Backtesting Platform

Regime-aware, risk-adjusted, overfitting-controlled strategy evaluation for Indian
equities. Built as the BCS685 major project (K.S. Institute of Technology, batch
2026_CSE_01).

> **Base paper:** "Enhancing Stock Market Prediction: A Robust LSTM-DNN Model..."
> (Alam et al., IEEE Access 2024). We extend its insight: *prediction alone is
> insufficient* — this platform adds the evaluation layer Indian retail lacks.

## The problem (SEBI evidence)

- 93% of individual F&O traders lost money FY22–FY24; ~₹1.8 lakh crore aggregate losses.
- SEBI's prescribed remedy: "improved financial education and investor awareness."

This platform is that education layer: it shows *which* strategy suits *which*
market regime, and tells you whether a backtest is trustworthy (PBO / Deflated
Sharpe), instead of a pretty but overfit equity curve.

## Quick start

```bash
git clone <repo-url>
cd indian-portfolio-intelligence
cp .env.example .env
uv sync                          # install deps (Python 3.11)
make dev                         # boot api + worker + redis + postgres + streamlit
make seed                        # (worker stack) backfill NIFTY-50 parquet cache
```

Then open the Streamlit dashboard at http://localhost:8501 and the API docs at
http://localhost:8888/docs.

For faster development without rebuilding application containers, run only
required infrastructure and start app processes locally:

```bash
make infra       # Postgres + Redis only
make api         # FastAPI at http://localhost:8888
make worker      # Celery worker, separate terminal
make frontend    # Streamlit at http://localhost:8501
```

## Modules

| Module | Purpose |
|---|---|
| `app/data` | OHLCV ingestion (yfinance/nsepython) + parquet cache + adjustment validation |
| `app/features` | Indicator/feature construction (pure functions) |
| `app/regime` | Gaussian HMM detection + RF ex-ante prediction + k-means baselines |
| `app/backtest` | vectorbt engine, 5 strategies, canonical metrics |
| `app/risk` | EWMA/GARCH vol, VaR, Expected Shortfall |
| `app/recommend` | regime → strategy suitability |
| `app/validation` | walk-forward / CPCV / PBO / Deflated Sharpe / costs |
| `app/report` | Plotly charts + trust reports |
| `app/api` | FastAPI endpoints (thin orchestration) |

## Documentation

- [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) — full architecture, decisions, iterations.
- [`docs/team/`](docs/team/) — per-teammate work guides (start with your own file).

## Development

```bash
make test        # pytest (unit)
make lint        # ruff
make typecheck   # mypy
make format      # ruff format
```

Conventional Commits, feature branches, PR required for `main` (see
`docs/IMPLEMENTATION_PLAN.md` §7).

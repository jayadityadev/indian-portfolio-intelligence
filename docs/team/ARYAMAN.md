# Aryaman Tiwari — Charts & Frontend

## Role
You own everything the user *sees*: the Plotly chart builders and the frontend
(Streamlit for iteration 1, Next.js for iteration 2). You consume only the API —
you never implement metrics or business logic in the frontend.

## You own (files)
| Area | Files |
|---|---|
| Charts | `app/report/charts.py` (backend Plotly → JSON) |
| Frontend (iter-1) | `frontend/streamlit/app.py` |
| Frontend (iter-2) | `frontend/nextjs/` (Next.js + TradingView Charting Library) |

## You do NOT own
- `app/backtest/*`, `app/regime/*`, `app/risk/*` → Jayaditya / Durgashree compute
  the numbers; you render them.
- `app/recommend/*` → Jayaditya (you render the `Recommendation` JSON).
- `scripts/*` → Chirag.

## The API contract you consume
Every endpoint returns `{"ok": true, "data": ...}` or
`{"ok": false, "error": {"code", "message"}}`. Dates are ISO `YYYY-MM-DD`, series
are arrays of `{"date", "value"}` (or object records). NaN becomes `null`. See
`app/schemas.py` and `../IMPLEMENTATION_PLAN.md` §15 for the endpoint table.

**Do not parse around an awkward endpoint shape** — request a `[contracts]` change.

Plotly figures are served by thin `app/api/report.py` endpoints. Streamlit only
fetches API JSON and renders it; it does not import chart builders or calculate
metrics. Strategy keys come from `/api/v1/market/strategies`.

## Iteration 1 tasks

### 1. Chart builders (`app/report/charts.py`)
- [x] Each returns valid Plotly JSON (use `plotly.graph_objects`, `.to_json()`):
  - price + regime-shaded timeline (input: OHLCV records + `RegimeResult`)
  - equity curve vs benchmark (input: `BacktestResult.equity_curve`)
  - drawdown chart
  - per-strategy metric comparison bars (input: `CompareReport`)
  - suitability bars (input: `Recommendation.suitability`)
  - trade scatter
- [x] Handle NaN → null, empty states, and long series (downsample to ≤2000 points).
- **Verify:** each builder unit-tests that output JSON parses and has the expected
  trace keys.

### 2. Streamlit dashboard (`frontend/streamlit/app.py`)
Pages (sidebar): Market · Backtest · Regime · Risk · Recommend.
- [x] Symbol picker + price chart + quick stats.
- [x] Backtest: pick symbol/strategy/params → `POST /backtest` → poll job → show
      equity + metrics table + drawdown.
- [x] Regime: regime timeline shaded on price + current regime + confidence.
- [x] Risk: vol, VaR, ES, drawdown panel.
- [x] Recommend: current regime → suggested strategy + suitability bars + rationale.
- **Verify:** full demo path works against a running stack (`make dev` + `make seed`).

## Iteration 2 tasks
- [ ] `frontend/nextjs/`: reproduce all pages in Next.js (App Router), deploy on Vercel.
- [ ] Embed the **TradingView Charting Library** (free embed) with a custom Datafeed
      wrapping `/market/{symbol}/series` and `/regime/{symbol}/timeline` for shading.
- [ ] Report export (PDF/HTML) of the trust report.
- [ ] Configure CORS + `NEXT_PUBLIC_API_URL` for the VM backend.

## Gotchas
- **Strategy keys are a shared constant** (`buy_and_hold`, `ma_crossover`, `rsi`,
  `momentum`, `mean_reversion`). Don't duplicate these strings in the frontend —
  read them from the API or import from `app/schemas.py`.
- Streamlit is a thin client: no pandas/metric computations in `app.py`.
- Poll jobs with a progress indicator; handle `failed` status gracefully (show the
  error, don't crash the page).

## Verify checklist
```
uv run ruff check app tests scripts
uv run mypy app
uv run pytest tests/unit
# manual: make dev && make seed, click through all 5 pages
```

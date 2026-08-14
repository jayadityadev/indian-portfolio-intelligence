# Chirag T — Data Pipeline Scripts, Ops, Slides

## Role
You own the **data pipeline scripts** that backfill and keep the market data fresh,
the **Postgres symbols seed**, **production ops**, and the **slides/demo support**.
A bad parquet cache silently corrupts every downstream module, so you are the data
quality gate.

## You own (files)
| Area | Files |
|---|---|
| Seed | `scripts/seed_universe.py` |
| Sync | `scripts/sync_daily.py` |
| Validate | `scripts/validate_data.py` |
| Symbols | Postgres `symbols` table seed |
| Ops | prod runbook notes, daily-sync cron |
| Slides | PPT + demo-run support |

## You do NOT own
- `app/data/*` adapters → Jayaditya (you *call* them; signatures are stubbed and
  frozen — see below).
- `app/features/*`, `app/risk/*` → Durgashree.
- `app/backtest/*`, `app/regime/*` → Jayaditya.
- Frontend/charts → Aryaman.

## The interface you build on (already stubbed — code against it today)
```python
from app.data.sources import fetch            # fetch(symbol, start, end, source=None) -> MarketDataFrame
from app.data.cache import (                  # load / store / latest_date / manifest_is_valid
    load, store, latest_date, manifest_is_valid,
)
from app.data.universe import nifty50_symbols, nifty50_index
from app.data.adjust import validate_adjustment
from app.schemas import MarketDataFrame, SymbolInfo
```
These signatures are frozen. If you need a change, open a `[contracts]` PR — don't
reimplement data fetching inside `scripts/`.

## Iteration 1 tasks

### 1. Seed (`scripts/seed_universe.py`)
- [ ] Iterate `nifty50_symbols()` + `nifty50_index()`, call `fetch(...)` for ~20
      years, `store(...)` each, print a progress summary.
- [ ] Populate Postgres `symbols` (symbol, name, exchange, index_member, isin,
      sector) — sector from nsepython index constituents.
- **Acceptance:** `make seed` completes with zero source errors; manifest hashes
  consistent; ≥20 symbols valid; every symbol `adjusted=True`.

### 2. Daily sync (`scripts/sync_daily.py`)
- [ ] For each symbol, `latest_date(...)` then `fetch` only newer rows and append.
- [ ] Idempotent — safe to re-run; no duplicate rows.
- **Acceptance:** re-running same day changes nothing.

### 3. Validate (`scripts/validate_data.py`)
- [ ] Run `validate_adjustment(...)` over the universe; spot-check a sample vs
      Twelve Data if `TWELVEDATA_API_KEY` is set; fail loudly on anomalies.
- **Acceptance:** passes for ≥20 symbols; flags any unadjusted series.

## Iteration 2 tasks
- [ ] Seed the full universe on the production VM; run `validate_data` there.
- [ ] Set up the daily-sync cron on prod.
- [ ] Write the ops/runbook notes (how to reseed, what logs mean, how to recover).
- [ ] Own the PPT/slides; keep screenshots in sync with the actual running demo.

## Gotchas
- **Never commit data files.** `data/` and `mlruns/` are gitignored; the cache is
  rebuilt via `make seed`.
- Keep scripts thin: orchestration only. All source/cache logic lives in `app/data`.
- Use `MarketData` objects end-to-end; don't reach into raw DataFrames with ad-hoc
  column names (`open/high/low/close/volume` is the canonical order).

## Verify checklist
```
uv run ruff check app tests scripts
uv run mypy app
uv run pytest tests/unit
# manual: make seed && make validate-data
```

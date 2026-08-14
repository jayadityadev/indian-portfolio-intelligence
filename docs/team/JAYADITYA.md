# Jayaditya Dev — Backend Core Lead

## Role
You own the **architecture, the contracts, and every correctness-critical backend
module**. Everything that is ML-critical or where a silent bug corrupts results
is yours. You also review every PR and enforce the git/CI rules.

## You own (files)
| Area | Files |
|---|---|
| Contracts | `app/schemas.py` (frozen), `app/config.py` |
| Data adapters | `app/data/sources.py`, `cache.py`, `universe.py`, `adjust.py` |
| Regime | `app/regime/hmm.py`, `rf.py`, `baselines.py`, `validate.py` |
| Backtest | `app/backtest/engine.py`, `strategies.py`, `metrics.py`, `portfolio.py` |
| Validation | `app/validation/walk_forward.py`, `cpcv.py`, `pbo.py`, `dsr.py`, `costs.py` |
| Recommendation | `app/recommend/scoring.py`, `service.py` |
| ML demo | `app/ml/lstm_dnn.py`, `artifacts.py` |
| API orchestration | `app/api/*` |
| Infra | `docker/*`, `docker-compose.yml`, `.github/workflows/ci.yml`, `Makefile`, `pyproject.toml` |

## You do NOT own
- `app/features/*` → Durgashree (you *consume* it — hold her to the column contract).
- `app/risk/*` → Durgashree.
- `app/report/charts.py` → Aryaman.
- `scripts/*` orchestration + Postgres `symbols` seed → Chirag (he *consumes* your `app/data` signatures).
- Frontend → Aryaman.

## Iteration 1 tasks (order matters)

### 1. Finish `app/data` adapters (deliver FIRST — unblocks Chirag)
- [ ] `sources.py`: `fetch(symbol, start, end, source)` — yfinance primary, nsepython fallback, `auto_adjust=True`. Verify `.NS`/`^NSEI` work and split-adjustment is correct.
- [ ] `cache.py`: `load`/`store`/`latest_date`/`manifest_is_valid` + parquet manifest.
- [ ] `adjust.py`: `validate_adjustment` raw-vs-adjusted check.
- [ ] `universe.py`: NIFTY-50 symbols + `^NSEI`.
- **Verify:** `uv run pytest` + a manual 3-symbol backfill writes valid parquet.

### 2. Regime detection (`app/regime`)
- [ ] `hmm.py`: Gaussian HMM 3-state; stable label convention (bear/sideways/bull by mean return).
- [ ] `baselines.py` (k-means, Wasserstein k-means) + `validate.py` (Davies-Bouldin, Dunn, MMD).
- [ ] Wire `/api/v1/regime/{symbol}/timeline`.
- **Consumes:** `FEATURE_COLUMNS` from Durgashree — reconfirm names at kickoff.

### 3. Backtest engine + metrics (`app/backtest`)
- [ ] `strategies.py`: the 5 strategies (registry keys: `buy_and_hold`, `ma_crossover`, `rsi`, `momentum`, `mean_reversion`).
- [ ] `engine.py`: vectorbt wrapper → `BacktestResult`; backtrader fallback.
- [ ] `metrics.py`: **single implementation** of every `PerformanceMetrics` field (§13 of plan). Reject duplicate metric math in review.
- [ ] `costs.py`: Indian brokerage/STT/stamp/slippage; net-of-costs default.
- [ ] Wire `/api/v1/backtest` + job poll/result endpoints.
- **Verify:** hand-check metrics on a tiny fixture; write a unit test with known answers.

### 4. Recommendation v1 (`app/recommend`, pair with Durgashree)
- [ ] `scoring.py` regime→strategy suitability matrix (rule-based v1).
- [ ] `service.py` → `Recommendation` (always includes the "not investment advice" caveat).
- [ ] Wire `/api/v1/recommend/{symbol}`.

## Iteration 2 tasks (schedule validation FIRST — it is the differentiator)
- [ ] `validation/`: walk-forward + CPCV (purge+embargo) + PBO + Deflated Sharpe; wire `TrustReport` into results.
- [ ] `regime/rf.py`: KMRF-style ex-ante regime predictor + SHAP importances; feed recommendation confidence.
- [ ] `backtest/portfolio.py`: multi-symbol equal-weight rebalance + regime-rotation demo.
- [ ] `ml/lstm_dnn.py`: bounded demo with the "insufficient alone" banner.
- [ ] Cloud deploy: Oracle free VM docker-compose prod + CI deploy step.

## Non-negotiable rules you enforce
1. `metrics.py` is the only place metrics are computed.
2. No data leakage — walk-forward/CPCV with purge+embargo; add a test that asserts the embargo gap.
3. Contract changes go through a `[contracts]` PR (schemas + docs together).
4. You set the CI; nobody merges red.

## Verify checklist (your PRs)
```
uv run ruff check app tests scripts
uv run mypy app
uv run pytest tests/unit
```

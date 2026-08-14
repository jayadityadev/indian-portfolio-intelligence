# Durgashree M — Features, Risk, Report Writing

## Role
You build the **feature-engineering** and **risk** layers, and you own the
**project report / methodology writing**. Your features are consumed by three
modules (regime, backtest, recommend), so your column names are a hard contract —
see below.

## You own (files)
| Area | Files |
|---|---|
| Features | `app/features/indicators.py`, `target.py` |
| Risk | `app/risk/volatility.py`, `var.py`, `stress.py` (iter-2) |
| Report | `docs/Report and PPT/` content, methodology chapters, results tables |

## You do NOT own
- `app/regime/*`, `app/backtest/*`, `app/recommend/*` → Jayaditya (he consumes your features).
- `app/report/charts.py` → Aryaman (he visualizes; you supply numbers).
- `scripts/*` → Chirag.

## The contract you must never break
`app/schemas.py` defines `FEATURE_COLUMNS`. Your `indicators.py` must emit a
`DataFrame` indexed by date with a `close` column **plus exactly these names**
(no renames without a `[contracts]` PR):

```
returns_pct, log_return, vol_20, vol_ewma,
sma_20, sma_50, sma_200, ema_12, ema_26,
rsi_14, macd, macd_signal, momentum_20, momentum_60,
atr_14, max_drawdown_rolling
```

Functions must be **pure** (`DataFrame -> DataFrame`, no I/O) so they are unit
testable against `tests/fixtures/`.

Canonical entry point: `add_indicators(frame: pd.DataFrame) -> pd.DataFrame`.
Leading rolling-window NaNs stay unchanged; `app/risk/report.py` assembles
`RiskReport` while API routing remains thin.

## Iteration 1 tasks

### 1. Features (`app/features/indicators.py`)
- [x] Implement every `FEATURE_COLUMNS` column. Use the `ta` library (installed)
      where convenient, manual pandas otherwise. Document NaN policy (first N rows
      are NaN for lookback indicators — keep them, do not forward-fill arbitrarily).
- [x] `target.py`: forward-return bins + regime label windows. **No lookahead** —
      labels at time `t` use data through `t` only (shift the target back).
- [x] Unit tests for a few indicators against hand-computed values on a tiny fixture.
- **Verify:** `uv run pytest tests/unit/test_features.py` (deterministic fixture tests).

### 2. Risk (`app/risk`)
- [x] `volatility.py`: EWMA volatility (iter-1; GARCH(1,1) is iter-2).
- [x] `var.py`: historical VaR 95/99, Expected Shortfall, parametric VaR, 1-day horizon.
- [x] Wire `/api/v1/risk/{symbol}` → `RiskReport`.
- **Verify:** RiskReport matches hand-computed EWMA/VaR on a fixture within tolerance.

### 3. Recommendation support (with Jayaditya)
- [x] Help define the regime→strategy suitability matrix logic in
      `app/recommend/scoring.py` (you contribute the finance rationale; Jayaditya
      wires the service).

## Iteration 2 tasks
- [ ] `volatility.py`: GARCH(1,1) 1- and 5-day vol forecast (check stationarity first).
- [ ] `stress.py`: VAE stress scenarios (paper #7) — synthetic scenarios, portfolio
      level, stress VaR/ES.
- [ ] **Report**: write the full methodology + results chapters. Pull every number
      from validated (PBO/DSR) results, never ad-hoc. Include the SEBI problem
      chapter (93% losses / ₹1.8 lakh crore / "education" remedy).

## Gotchas
- Don't forward-fill NaNs early in the series to "make charts pretty" — it changes
  downstream vol/momentum numbers and Jayaditya's regime fit.
- Keep risk pure: inputs = returns/`FeaturesFrame`, output = numbers. No charts, no
  API logic — Aryaman visualizes.
- Document every formula you implement in a docstring (report chapter will reuse it).

## Verify checklist
```
uv run ruff check app tests scripts
uv run mypy app
uv run pytest tests/unit
```

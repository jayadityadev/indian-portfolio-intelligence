# ADR-000 — Iteration-2 Design Decisions (Grill Output)

Status: Accepted
Date: 2026-08-15
Decider: Jayaditya Dev (grill session, guided by grill-with-docs)

This ADR records the sharpened design decisions for Iteration 2. Each decision
resolves an ambiguity in `docs/IMPLEMENTATION_PLAN.md` §18 that the grill session
surfaced. All decisions were taken with the research grounding from papers #7,
#10, #11, and #12.

---

## Context

Iteration 1 is complete (v1.0.0). Iteration 2 adds the credibility layer
(walk-forward, CPCV, PBO, DSR), the RF regime predictor, portfolio backtesting,
GARCH, VAE stress testing, the LSTM-DNN base-paper demo, a Next.js frontend with
TradingView, and cloud deploy.

The plan lists these work packages but leaves several computational-scope and
ordering decisions open. The grill resolved the consequential ones.

---

## Decisions

### D-1 — V1 validation scope: walk-forward + PBO/DSR headline, CPCV marked `slow`

The headline credibility numbers are walk-forward out-of-sample results plus PBO
and DSR across a strategy×params config grid. CPCV is implemented and unit-tested
for leakage (embargo assertion) but the full combinatorial run is marked
`@pytest.mark.slow` so CI stays fast and the demo stays responsive.

Rationale: CPCV generates C(N,k) paths; a full run on every request is slow.
Reusing the single vectorbt engine keeps metrics canonical. Plan §14.3/§14.5
(walk-forward everywhere, multiple-testing guard) are satisfied by WF+PBO+DSR.

### D-2 — PBO return matrix source: reuse `engine.run` per config

The CSCV performance matrix (returns per config) is built by looping the
strategy×params grid through the existing `app/backtest/engine.run`, extracting
daily equity returns per config, and assembling the T×N matrix. No new backtest
path. Reuses the canonical engine + `metrics.py`.

### D-3 — Embargo/purge policy: configurable, default = max(200, horizon), leakage test

`embargo_bars` defaults to `max(200, label_horizon)` — 200 covers `sma_200`; the
horizon covers forward-return labels. A unit test asserts every train/test sample
pair is separated by ≥ `embargo_bars`, enforcing plan §14.4 as an invariant.

### D-4 — V2 RF regime predictor feeds suitability confidence only, long-only

The RF predicts next-day regime ex ante (KMRF-style, paper #11) and its
probability feeds the recommendation suitability/confidence, replacing the
rule-based confidence in `recommend/service.py`. Paper #11 found RF regime
signals were *contrarian*; we do NOT act on shorts — we keep all strategies
long-only and document the contrarian finding honestly as a caveat. This fits
the retail-education positioning and the cash-equity long-only non-goal.

### D-5 — Build order: V1 → V2 → V4 → V5 → V3 → V6/V7 (frontend/cloud last)

The credibility core (validation + RF regime) ships first because it is the
differentiator and reuses the same engine + metrics. Then portfolio/rotation
(V4), GARCH (V5), VAE stress (V3). Next.js + TradingView (V6) and cloud deploy
(V7) are product polish, scheduled last. V8 (report) spans the whole effort.

### D-6 — V3 VAE stress: lightweight, MC stress, stress-VaR > historical by construction

A lightweight VAE (torch) trains on standardized returns, Monte-Carlo samples the
latent, decodes to stressed returns, and computes stress VaR/ES. Acceptance:
stress VaR > historical VaR by construction. The full three-stage PCA/AE/VAE
sectoral comparison from paper #7 is documented as future work, not shipped —
VAE training on a single-symbol demo may not converge meaningfully and torch is
heavy.

### D-7 — LSTM-DNN base-paper demo: shipped as demo-only with insufficiency banner

The LSTM-DNN next-close prediction endpoint ships to honor the base paper, is
walk-forward validated, is labeled "prediction alone is insufficient", and NEVER
feeds recommendations. It is a demo/diagnostic path only (plan §14.8).

### D-8 — V6 frontend salvage from `indian-market-portfolio` (old repo)

The old repo `https://github.com/jayadityadev/indian-market-portfolio` contains a
polished Next.js 16 / React 19 frontend. Its **presentational layer** is the
starting point for our V6 Next.js app, but its **data wiring is NOT reusable**
(its `api.ts` + `page.tsx` target the old single `POST /analyze` backend, not our
modular `/api/v1` REST contracts).

Salvage inventory for V6 (copy verbatim, then rewrite data wiring):
- `CandlestickChart.tsx` — lightweight-charts OHLCV + volume + regime background
  shading (exactly the chart our `/market/{symbol}/series` + `/regime/timeline`
  feed).
- `BeginnerView.tsx` — plain-language insight cards, regime timeline bar, risk
  forecast block.
- `ProView.tsx` — quant view: strategy comparison table, equity curves, regime-
  conditional CAGR heatmap, ML probability bars, CSV export.
- `StrategyLibrary.tsx` — educational strategy cards.
- `MagicBento.tsx` + `MagicBento.css` — animated landing hero.
- `ThemeToggle.tsx` — dark/light toggle with circular reveal.
- `globals.css` — design system: `--bull/--bear/--sideways` colors, light/dark
  theme vars, card/modal/metric-table styles.
- `layout.tsx` — Sora + Fraunces font loading.

Not reusable (rewrite against `/api/v1`): `api.ts`, `page.tsx` state logic.

Per D-5 (V6 deferred), these assets are NOT scaffolded into the repo during
V1–V5. They are inventoried here so V6 can assemble them against our API when it
begins.

---

## Consequences

- V1 and V2 are the highest-value, first-shipped packages.
- CPCV remains available but not in the default fast CI path.
- The long-only scope is preserved; the contrarian finding is documented, not traded.
- Heavy deps (torch for VAE, tensorflow for LSTM) are isolated behind the
  `ml`/stress optional extras so the core API stays lightweight.

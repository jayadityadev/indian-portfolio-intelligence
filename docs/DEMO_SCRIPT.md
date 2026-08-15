# Iteration 1 Demo Script

Purpose: demonstrate complete flow from adjusted Indian market data to a
regime-aware recommendation.

## 1. Start Stack

From fresh checkout:

```bash
cp .env.example .env
make dev
```

Verify:

- API docs: `http://localhost:8000/docs`
- Streamlit: `http://localhost:8501`
- Health: `curl http://localhost:8000/health`

In a second terminal, build the parquet cache:

```bash
make seed
```

Seed may take several minutes because it downloads roughly 20 years for the
NIFTY-50 universe. For a smoke run, use the worker container directly:

```bash
docker compose run --rm -e PARQUET_DIR=/data/parquet worker \
  uv run python -m scripts.seed_universe --symbols "^NSEI" RELIANCE.NS --years 2
```

## 2. Market Page

1. Open `http://localhost:8501`.
2. Select `^NSEI`.
3. Show adjusted close series and cached observation count.
4. Explain that data comes from parquet cache, not frontend calculations.

## 3. Backtest Page

1. Select `^NSEI` and `ma_crossover`.
2. Click **Run backtest**.
3. Show queued/running/succeeded job status.
4. Show equity vs benchmark, drawdown, and metrics.
5. Click **Compare all strategies**.
6. Show side-by-side comparison for:
   `buy_and_hold`, `ma_crossover`, `rsi`, `momentum`, `mean_reversion`.

## 4. Regime Page

1. Open **Regime**.
2. Show current bull/bear/sideways state and validation values.
3. Show regime-shaded price chart.

## 5. Risk Page

1. Open **Risk**.
2. Show EWMA volatility, VaR 95%, expected shortfall, and maximum drawdown.
3. State that risk values come from backend `RiskReport`.

## 6. Recommend Page

1. Open **Recommend**.
2. Show current regime, suggested strategy, suitability bars, rationale, and
   the “not investment advice” caveat.

## 7. Failure Path

1. Stop the worker with `docker compose stop worker`.
2. Submit a backtest.
3. Show frontend job failure/timeout handling.
4. Restart with `docker compose start worker`.

## 8. Cleanup

```bash
make down
```

Never commit `data/` parquet files or `.env` credentials.

Reference screenshots are stored in `docs/screenshots/`:
`market.png`, `backtest.png`, `regime.png`, `risk.png`, and `recommend.png`.

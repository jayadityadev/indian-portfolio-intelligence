"""Shared data contracts — THE integration backbone.

Every module consumes and produces the shapes defined here. Rules:

1. Time series flow internally as pandas objects (see the docstrings for the exact
   column layout). At any API/JSON boundary they are converted to plain records
   (``*.records`` or the ``to_records`` helpers below).
2. Do NOT invent ad-hoc dicts between modules. If you need a new field, change the
   schema here in the same PR and tag it ``[contracts]``.
3. All floats round-trip; never serialize NaN (convert to ``null`` at the boundary).

See docs/IMPLEMENTATION_PLAN.md §10 for the narrative version.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, cast

import pandas as pd
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Envelope + health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    ok: bool
    version: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class OkResponse(BaseModel):
    ok: bool
    data: dict | list | None = None
    error: ErrorDetail | None = None


# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------

# Canonical OHLCV column order for the internal pandas DataFrame.
OHLCV_COLUMNS: list[str] = ["open", "high", "low", "close", "volume"]

SourceName = Literal["yfinance", "nsepython", "twelvedata"]
Freq = Literal["1d"]


class MarketData(BaseModel):
    """A single symbol's time series.

    Internal pandas shape (indexed by a tz-aware ``DatetimeIndex`` named ``date``):
        DataFrame[OHLCV_COLUMNS], float64 columns.
    ``adjusted=True`` means split/dividend adjusted (mandatory for backtests).
    """

    symbol: str
    source: SourceName
    adjusted: bool
    freq: Freq = "1d"
    fetched_at: datetime


@dataclass
class MarketDataFrame:
    """Internal market-data value carrying metadata and pandas OHLCV data.

    Pydantic ``MarketData`` remains the JSON metadata contract. This wrapper keeps
    DataFrame operations out of API schemas while preserving the §10.1 shape.
    """

    symbol: str
    source: SourceName
    adjusted: bool
    frame: pd.DataFrame
    freq: Freq = "1d"
    fetched_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.frame.index, pd.DatetimeIndex):
            raise TypeError("market data frame must use DatetimeIndex")
        if self.frame.index.name != "date":
            self.frame.index = self.frame.index.rename("date")
        missing = [column for column in OHLCV_COLUMNS if column not in self.frame.columns]
        if missing:
            raise ValueError(f"market data missing columns: {missing}")
        self.frame = self.frame.loc[:, OHLCV_COLUMNS].astype(float)

    @property
    def metadata(self) -> MarketData:
        return MarketData(
            symbol=self.symbol,
            source=self.source,
            adjusted=self.adjusted,
            freq=self.freq,
            fetched_at=self.fetched_at or datetime.now(),
        )

    def to_records(self) -> list[dict[str, object]]:
        """Serialize OHLCV rows using ISO dates and JSON-safe nulls."""
        frame = self.frame.reset_index()
        frame["date"] = pd.to_datetime(frame["date"]).dt.date.astype(str)
        frame = frame.where(frame.notna(), None)
        return cast(list[dict[str, object]], frame.to_dict(orient="records"))


class OhlcvRecord(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


class SymbolInfo(BaseModel):
    symbol: str
    name: str
    exchange: Literal["NSE", "BSE"]
    index_member: bool = False
    isin: str | None = None
    sector: str | None = None


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------
#
# FeaturesFrame internal pandas shape (indexed by date), `close` plus at least:
#   returns_pct, log_return, vol_20, vol_ewma,
#   sma_20, sma_50, sma_200, ema_12, ema_26,
#   rsi_14, macd, macd_signal, momentum_20, momentum_60,
#   atr_14, max_drawdown_rolling, regime_label (int, filled by regime module).
# ---------------------------------------------------------------------------

FEATURE_COLUMNS: list[str] = [
    "returns_pct",
    "log_return",
    "vol_20",
    "vol_ewma",
    "sma_20",
    "sma_50",
    "sma_200",
    "ema_12",
    "ema_26",
    "rsi_14",
    "macd",
    "macd_signal",
    "momentum_20",
    "momentum_60",
    "atr_14",
    "max_drawdown_rolling",
]


# ---------------------------------------------------------------------------
# Regime
# ---------------------------------------------------------------------------

RegimeMethod = Literal["hmm", "kmeans", "wkmeans"]


class RegimeValidation(BaseModel):
    davies_bouldin: float | None = None
    dunn_index: float | None = None
    mmd: float | None = None
    transition_matrix: list[list[float]] | None = None


class RegimeResult(BaseModel):
    symbol: str
    method: RegimeMethod
    n_states: int
    labels: list[int]  # per-timestamp state id
    state_names: dict[int, str]  # e.g. {0: "bear", 1: "sideways", 2: "bull"}
    log_likelihood: float | None = None
    validation: RegimeValidation | None = None
    fitted_at: datetime


class RegimePoint(BaseModel):
    date: date
    state: int
    state_name: str


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

StrategyName = Literal["buy_and_hold", "ma_crossover", "rsi", "momentum", "mean_reversion"]
STRATEGY_NAMES: tuple[StrategyName, ...] = (
    "buy_and_hold",
    "ma_crossover",
    "rsi",
    "momentum",
    "mean_reversion",
)


class PerformanceMetrics(BaseModel):
    """Canonical metric set. Computed ONLY by ``backtest/metrics.py``."""

    cagr: float
    total_return_pct: float
    sharpe: float
    sortino: float
    calmar: float
    information_ratio: float
    max_drawdown_pct: float
    annualized_vol_pct: float
    win_rate_pct: float
    profit_factor: float
    avg_win_pct: float
    avg_loss_pct: float
    num_trades: int
    exposure_pct: float
    benchmark_return_pct: float
    alpha_pct: float
    beta: float


class EquityPoint(BaseModel):
    date: date
    equity: float
    benchmark: float


class Trade(BaseModel):
    entry_date: date
    exit_date: date
    direction: Literal["long", "short"]
    pnl_pct: float
    bars_held: int


class TrustReport(BaseModel):
    """Backtest credibility summary, produced by the ``validation`` module."""

    method: Literal["walk_forward", "cpcv"] | None = None
    n_folds: int | None = None
    out_of_sample_sharpe: float | None = None
    pbo: float | None = None  # Probability of Backtest Overfitting [0,1]
    deflated_sharpe: float | None = None
    expected_max_sharpe: float | None = None
    embargo_bars: int | None = None
    caveats: list[str] = Field(default_factory=list)


class BacktestResult(BaseModel):
    symbol: str
    strategy: StrategyName
    params: dict = Field(default_factory=dict)
    start: date
    end: date
    regime_method: str | None = None
    net_of_costs: bool = True
    metrics: PerformanceMetrics
    equity_curve: list[EquityPoint]
    trade_list: list[Trade]
    trust: TrustReport | None = None


class CompareReport(BaseModel):
    symbol: str
    start: date
    end: date
    net_of_costs: bool = True
    results: list[BacktestResult]


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------


class RiskReport(BaseModel):
    symbol: str
    method: Literal["ewma", "garch"] = "ewma"
    annualized_vol_pct: float
    ewma_vol_pct: float | None = None
    garch_vol_pct: float | None = None
    var_95_pct: float
    var_99_pct: float
    expected_shortfall_95_pct: float
    max_drawdown_pct: float
    horizon: str = "1d"


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------


class Recommendation(BaseModel):
    symbol: str
    current_regime: dict  # {"state_name": str, "confidence": float}
    suggested_strategy: StrategyName
    rationale: list[str]
    suitability: dict[str, float]  # strategy -> score
    caveat: str


# ---------------------------------------------------------------------------
# Jobs (async)
# ---------------------------------------------------------------------------

JobStatusName = Literal["queued", "running", "succeeded", "failed"]


class JobStatus(BaseModel):
    job_id: str
    status: JobStatusName
    progress_pct: int | None = None
    result_ref: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# LSTM-DNN demo (base-paper honor, never a signal source)
# ---------------------------------------------------------------------------


class PricePrediction(BaseModel):
    symbol: str
    next_close: float
    caveat: str = (
        "Research/diagnostic only. Prediction alone is insufficient — see the evaluation layer."
    )

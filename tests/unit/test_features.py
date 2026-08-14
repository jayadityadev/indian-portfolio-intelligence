import pandas as pd
import pytest
from fixtures.data import make_ohlcv

from app.features.indicators import add_indicators, ewma_volatility
from app.features.target import forward_return_bins, regime_label_windows
from app.schemas import FEATURE_COLUMNS


def test_indicators_emit_canonical_columns_and_preserve_nan() -> None:
    result = add_indicators(make_ohlcv())
    assert list(result.columns) == [
        "open",
        "high",
        "low",
        "close",
        "volume",
        *FEATURE_COLUMNS,
    ]
    assert result["sma_200"].iloc[:199].isna().all()
    assert result["sma_200"].iloc[-1] == pytest.approx(result["close"].iloc[-200:].mean())


def test_ewma_uses_squared_returns() -> None:
    returns = pd.Series([0.1, 0.0, 0.0])
    result = ewma_volatility(returns, lambda_=0.5)
    assert result.iloc[-1] == pytest.approx(0.05)


def test_targets_are_shifted_and_do_not_label_future_tail() -> None:
    close = pd.Series([100.0, 101.0, 102.0, 120.0, 121.0])
    bins = forward_return_bins(close, horizon=1, n_bins=2)
    labels = regime_label_windows(close, horizon=1, bull_threshold=0.05, bear_threshold=-0.05)
    assert bins.iloc[-1] != bins.iloc[-1]
    assert labels.iloc[-1] != labels.iloc[-1]
    assert labels.iloc[2] == 2

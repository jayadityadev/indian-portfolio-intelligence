"""Shared API dependencies and feature loading boundary."""

from __future__ import annotations

import pandas as pd

from app.data.cache import load


def load_market_frame(symbol: str) -> pd.DataFrame:
    return load(symbol).frame


def load_features(symbol: str) -> pd.DataFrame:
    """Delegate feature construction to feature module owned by Durgashree."""
    from app.features.indicators import add_indicators

    return add_indicators(load_market_frame(symbol))

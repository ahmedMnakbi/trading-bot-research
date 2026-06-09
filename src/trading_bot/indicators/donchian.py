from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DonchianChannel:
    upper: pd.Series
    lower: pd.Series
    middle: pd.Series


def donchian_channel(candles: pd.DataFrame, lookback: int) -> DonchianChannel:
    if lookback < 2:
        raise ValueError("lookback must be at least 2")
    missing = {"high", "low"}.difference(candles.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    if (candles[["high", "low"]] <= 0).any().any():
        raise ValueError("prices must be positive")
    upper = candles["high"].rolling(window=lookback, min_periods=lookback).max()
    lower = candles["low"].rolling(window=lookback, min_periods=lookback).min()
    return DonchianChannel(upper=upper, lower=lower, middle=(upper + lower) / 2)


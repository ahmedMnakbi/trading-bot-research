from __future__ import annotations

import pandas as pd


def typical_price(candles: pd.DataFrame) -> pd.Series:
    return (candles["high"] + candles["low"] + candles["close"]) / 3


def vwap(candles: pd.DataFrame, window: int | None = None) -> pd.Series:
    price = typical_price(candles)
    volume = candles["volume"].replace(0, pd.NA)
    price_volume = price * volume
    if window is None:
        cumulative_volume = volume.cumsum()
        return price_volume.cumsum() / cumulative_volume
    rolling_volume = volume.rolling(window=window, min_periods=window).sum()
    return price_volume.rolling(window=window, min_periods=window).sum() / rolling_volume


def rolling_noise_band(candles: pd.DataFrame, window: int, multiple: float) -> pd.Series:
    if window < 2:
        raise ValueError("window must be at least 2")
    returns = candles["close"].pct_change().abs()
    return returns.rolling(window=window, min_periods=window).mean() * multiple

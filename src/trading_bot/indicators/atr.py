from __future__ import annotations

import pandas as pd


def average_true_range(candles: pd.DataFrame, period: int) -> pd.Series:
    if period < 1:
        raise ValueError("period must be positive")
    _require_columns(candles, {"high", "low", "close"})
    if (candles[["high", "low", "close"]] <= 0).any().any():
        raise ValueError("prices must be positive")
    previous_close = candles["close"].shift(1)
    true_range = pd.concat(
        [
            candles["high"] - candles["low"],
            (candles["high"] - previous_close).abs(),
            (candles["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window=period, min_periods=period).mean()


def _require_columns(candles: pd.DataFrame, columns: set[str]) -> None:
    missing = columns.difference(candles.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")


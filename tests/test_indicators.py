from __future__ import annotations

import pandas as pd
import pytest

from trading_bot.indicators.atr import average_true_range
from trading_bot.indicators.donchian import donchian_channel
from trading_bot.indicators.moving_average import exponential_moving_average


def sample_candles() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "high": [10, 12, 13, 15],
            "low": [8, 9, 10, 12],
            "close": [9, 11, 12, 14],
        }
    )


def test_atr_calculation_on_known_sample_data() -> None:
    atr = average_true_range(sample_candles(), 2)

    assert pd.isna(atr.iloc[0])
    assert atr.iloc[1] == 2.5
    assert atr.iloc[2] == 3.0


def test_atr_rejects_non_positive_prices() -> None:
    candles = sample_candles()
    candles.loc[0, "high"] = 0

    with pytest.raises(ValueError, match="positive"):
        average_true_range(candles, 2)


def test_ema_calculation_alignment() -> None:
    values = pd.Series([1, 2, 3, 4])
    ema = exponential_moving_average(values, 2)

    assert list(ema.index) == list(values.index)
    assert ema.iloc[0] == 1


def test_donchian_channel_uses_previous_channel_for_breakout_comparison() -> None:
    candles = pd.DataFrame({"high": [10, 11, 12, 13], "low": [5, 6, 7, 8], "close": [6, 7, 8, 14]})
    channel = donchian_channel(candles, 3)

    assert channel.upper.iloc[-2] == 12
    assert candles["close"].iloc[-1] > channel.upper.iloc[-2]


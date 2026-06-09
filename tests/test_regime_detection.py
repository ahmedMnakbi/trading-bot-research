from __future__ import annotations

import pandas as pd

from trading_bot.validation.regime import tag_regimes


def test_regime_detection_labels_uptrend_correctly() -> None:
    candles = pd.DataFrame({"close": list(range(1, 30))})

    tagged = tag_regimes(
        candles,
        trend_ma_period=5,
        volatility_window=3,
        high_volatility_quantile=0.75,
        low_volatility_quantile=0.25,
    )

    assert tagged["trend_regime"].iloc[-1] == "uptrend"


def test_regime_detection_labels_downtrend_correctly() -> None:
    candles = pd.DataFrame({"close": list(range(30, 1, -1))})

    tagged = tag_regimes(
        candles,
        trend_ma_period=5,
        volatility_window=3,
        high_volatility_quantile=0.75,
        low_volatility_quantile=0.25,
    )

    assert tagged["trend_regime"].iloc[-1] == "downtrend"


def test_regime_detection_labels_range_correctly() -> None:
    candles = pd.DataFrame({"close": [100] * 30})

    tagged = tag_regimes(
        candles,
        trend_ma_period=5,
        volatility_window=3,
        high_volatility_quantile=0.75,
        low_volatility_quantile=0.25,
    )

    assert tagged["trend_regime"].iloc[-1] == "range"


def test_regime_detection_marks_high_volatility_candles() -> None:
    candles = pd.DataFrame({"close": [100, 101, 99, 102, 80, 120, 70, 130, 90, 150]})

    tagged = tag_regimes(
        candles,
        trend_ma_period=3,
        volatility_window=2,
        high_volatility_quantile=0.75,
        low_volatility_quantile=0.25,
    )

    assert "high_volatility" in set(tagged["volatility_regime"])


def test_regime_detection_handles_insufficient_ma_data_as_unknown() -> None:
    candles = pd.DataFrame({"close": [1, 2, 3]})

    tagged = tag_regimes(
        candles,
        trend_ma_period=5,
        volatility_window=2,
        high_volatility_quantile=0.75,
        low_volatility_quantile=0.25,
    )

    assert tagged["trend_regime"].iloc[-1] == "unknown"


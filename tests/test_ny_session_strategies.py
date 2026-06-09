from datetime import UTC, datetime, timedelta

import pandas as pd

from trading_bot.ny_session.models import NySessionSignal
from trading_bot.ny_session.strategies import (
    DynamicNoiseBandVwap,
    LondonNyOverlapMomentum,
    OpeningRangeBreakout,
    VolumeVolatilityExpansion,
    VwapTrendContinuation,
    get_ny_session_strategy,
)


def _trend_candles(rows: int = 60, *, start: datetime | None = None) -> pd.DataFrame:
    start = start or datetime(2026, 7, 15, 12, 0, tzinfo=UTC)
    records = []
    price = 100.0
    for index in range(rows):
        timestamp = start + timedelta(minutes=5 * index)
        price += 0.2
        records.append(
            {
                "timestamp": timestamp,
                "new_york_timestamp": timestamp.astimezone(
                    pd.Timestamp(timestamp).tz_convert("America/New_York").tz
                ),
                "open": price - 0.1,
                "high": price + 0.5,
                "low": price - 0.5,
                "close": price,
                "volume": float(100 + index),
                "spread": 10,
            }
        )
    dataframe = pd.DataFrame(records)
    dataframe["new_york_timestamp"] = pd.to_datetime(
        dataframe["timestamp"],
        utc=True,
    ).dt.tz_convert("America/New_York")
    return dataframe


def test_strategy_registry_returns_known_strategy() -> None:
    strategy = get_ny_session_strategy("opening_range_breakout", {"max_spread": 20})

    assert isinstance(strategy, OpeningRangeBreakout)
    assert strategy.max_spread == 20


def test_opening_range_breakout_enters_after_range_break() -> None:
    candles = _trend_candles(30, start=datetime(2026, 7, 15, 13, 30, tzinfo=UTC))
    candles.loc[candles.index[-1], "close"] = candles["high"].iloc[:6].max() + 2
    candles.loc[candles.index[-1], "high"] = candles.loc[candles.index[-1], "close"] + 1

    result = OpeningRangeBreakout(max_spread=20).generate_signal(candles, len(candles) - 1)

    assert result.signal == NySessionSignal.ENTER_LONG
    assert result.stop_loss is not None
    assert result.stop_loss < float(candles["close"].iloc[-1])


def test_vwap_trend_continuation_emits_long_signal() -> None:
    candles = _trend_candles(60)

    result = VwapTrendContinuation(max_spread=20).generate_signal(candles, len(candles) - 1)

    assert result.signal == NySessionSignal.ENTER_LONG


def test_dynamic_noise_band_vwap_can_emit_long_signal() -> None:
    candles = _trend_candles(35)
    candles.loc[candles.index[-1], "close"] = float(candles["close"].iloc[-2]) * 1.05
    candles.loc[candles.index[-1], "high"] = float(candles["close"].iloc[-1]) + 1

    result = DynamicNoiseBandVwap(max_spread=20).generate_signal(candles, len(candles) - 1)

    assert result.signal == NySessionSignal.ENTER_LONG


def test_london_ny_overlap_momentum_respects_overlap_session() -> None:
    candles = _trend_candles(40, start=datetime(2026, 7, 15, 12, 0, tzinfo=UTC))
    candles.loc[candles.index[-1], "close"] = float(candles["high"].iloc[-13:-1].max()) + 2
    candles.loc[candles.index[-1], "high"] = float(candles["close"].iloc[-1]) + 1

    result = LondonNyOverlapMomentum(max_spread=20).generate_signal(candles, len(candles) - 1)

    assert result.signal == NySessionSignal.ENTER_LONG


def test_volume_volatility_expansion_emits_long_signal() -> None:
    candles = _trend_candles(30)
    candles.loc[candles.index[-1], "volume"] = float(candles["volume"].iloc[-21:-1].mean()) * 3
    candles.loc[candles.index[-1], "open"] = 110
    candles.loc[candles.index[-1], "close"] = 120
    candles.loc[candles.index[-1], "high"] = 122
    candles.loc[candles.index[-1], "low"] = 108

    result = VolumeVolatilityExpansion(max_spread=20).generate_signal(candles, len(candles) - 1)

    assert result.signal == NySessionSignal.ENTER_LONG


def test_strategy_skips_high_spread_and_news_blackout() -> None:
    candles = _trend_candles(60)
    candles.loc[candles.index[-1], "spread"] = 100

    spread_result = VwapTrendContinuation(max_spread=20).generate_signal(candles, len(candles) - 1)
    news_result = VwapTrendContinuation(news_blackout=True).generate_signal(
        candles,
        len(candles) - 1,
    )

    assert spread_result.signal == NySessionSignal.SKIP_SPREAD
    assert news_result.signal == NySessionSignal.SKIP_NEWS


def test_strategy_generates_session_close_for_position_after_hours() -> None:
    candles = _trend_candles(60, start=datetime(2026, 7, 15, 21, 0, tzinfo=UTC))

    result = VwapTrendContinuation().generate_signal(candles, len(candles) - 1, has_position=True)

    assert result.signal == NySessionSignal.SESSION_CLOSE

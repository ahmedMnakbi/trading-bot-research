from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from trading_bot.indicators.atr import average_true_range
from trading_bot.indicators.donchian import donchian_channel
from trading_bot.indicators.moving_average import exponential_moving_average
from trading_bot.ny_session.filters import NySessionFilter
from trading_bot.ny_session.indicators import rolling_noise_band, vwap
from trading_bot.ny_session.models import NySessionSignal, NySessionSignalResult


class SessionStrategy(Protocol):
    session_start: str
    session_end: str
    max_spread: int | None
    news_blackout: bool


@dataclass(frozen=True)
class OpeningRangeBreakout:
    name: str = "opening_range_breakout"
    session_start: str = "09:30"
    session_end: str = "16:00"
    opening_minutes: int = 30
    atr_period: int = 14
    atr_stop_multiple: float = 1.5
    max_spread: int | None = None
    news_blackout: bool = False

    def generate_signal(
        self, candles: pd.DataFrame, current_index: int, *, has_position: bool = False
    ) -> NySessionSignalResult:
        filtered = _filter(self, candles, current_index, has_position)
        if filtered is not None:
            return filtered
        history = candles.iloc[: current_index + 1].copy()
        if len(history) < max(self.atr_period, 3):
            return NySessionSignalResult.wait("insufficient_history")
        day = history.iloc[-1]["new_york_timestamp"].date()
        session_rows = history[history["new_york_timestamp"].dt.date == day]
        opening_rows = session_rows.head(max(1, self.opening_minutes // 5))
        if len(opening_rows) < max(1, self.opening_minutes // 5):
            return NySessionSignalResult(
                signal=NySessionSignal.SETUP_FORMING,
                reason="opening_range_forming",
            )
        upper = float(opening_rows["high"].max())
        lower = float(opening_rows["low"].min())
        close = float(history["close"].iloc[-1])
        atr = average_true_range(history, self.atr_period).iloc[-1]
        if pd.isna(atr) or atr <= 0:
            return NySessionSignalResult.wait("indicator_unavailable")
        if has_position:
            return _exit_if_mean_reverted(close, (upper + lower) / 2)
        if close > upper:
            return _entry(
                NySessionSignal.ENTER_LONG,
                close,
                close - float(atr) * self.atr_stop_multiple,
            )
        if close < lower:
            return _entry(
                NySessionSignal.ENTER_SHORT,
                close,
                close + float(atr) * self.atr_stop_multiple,
            )
        return NySessionSignalResult.wait("inside_opening_range", upper=upper, lower=lower)


@dataclass(frozen=True)
class VwapTrendContinuation:
    name: str = "vwap_trend_continuation"
    session_start: str = "08:00"
    session_end: str = "17:00"
    ema_period: int = 20
    atr_period: int = 14
    max_spread: int | None = None
    news_blackout: bool = False

    def generate_signal(
        self, candles: pd.DataFrame, current_index: int, *, has_position: bool = False
    ) -> NySessionSignalResult:
        filtered = _filter(self, candles, current_index, has_position)
        if filtered is not None:
            return filtered
        history = candles.iloc[: current_index + 1].copy()
        if len(history) < max(self.ema_period, self.atr_period, 3):
            return NySessionSignalResult.wait("insufficient_history")
        current_close = float(history["close"].iloc[-1])
        current_vwap = vwap(history).iloc[-1]
        ema = exponential_moving_average(history["close"], self.ema_period).iloc[-1]
        atr = average_true_range(history, self.atr_period).iloc[-1]
        if pd.isna(current_vwap) or pd.isna(ema) or pd.isna(atr):
            return NySessionSignalResult.wait("indicator_unavailable")
        if has_position and current_close < float(current_vwap):
            return NySessionSignalResult(signal=NySessionSignal.EXIT, reason="lost_vwap")
        if current_close > float(current_vwap) and current_close > float(ema):
            return _entry(
                NySessionSignal.ENTER_LONG,
                current_close,
                current_close - float(atr) * 1.5,
            )
        if current_close < float(current_vwap) and current_close < float(ema):
            return _entry(
                NySessionSignal.ENTER_SHORT,
                current_close,
                current_close + float(atr) * 1.5,
            )
        return NySessionSignalResult.wait("no_vwap_trend")


@dataclass(frozen=True)
class DynamicNoiseBandVwap:
    name: str = "dynamic_noise_band_vwap"
    session_start: str = "08:00"
    session_end: str = "17:00"
    noise_window: int = 20
    noise_multiple: float = 2.0
    max_spread: int | None = None
    news_blackout: bool = False

    def generate_signal(
        self, candles: pd.DataFrame, current_index: int, *, has_position: bool = False
    ) -> NySessionSignalResult:
        filtered = _filter(self, candles, current_index, has_position)
        if filtered is not None:
            return filtered
        history = candles.iloc[: current_index + 1].copy()
        if len(history) < self.noise_window + 2:
            return NySessionSignalResult.wait("insufficient_history")
        close = float(history["close"].iloc[-1])
        previous_close = float(history["close"].iloc[-2])
        band = rolling_noise_band(history, self.noise_window, self.noise_multiple).iloc[-1]
        current_vwap = vwap(history).iloc[-1]
        if pd.isna(band) or pd.isna(current_vwap):
            return NySessionSignalResult.wait("indicator_unavailable")
        upper = previous_close * (1 + float(band))
        lower = previous_close * (1 - float(band))
        if has_position and close < float(current_vwap):
            return NySessionSignalResult(signal=NySessionSignal.EXIT, reason="vwap_stop")
        if close > upper and close > float(current_vwap):
            return _entry(NySessionSignal.ENTER_LONG, close, float(current_vwap))
        if close < lower and close < float(current_vwap):
            return _entry(NySessionSignal.ENTER_SHORT, close, float(current_vwap))
        return NySessionSignalResult.wait("inside_noise_band", upper=upper, lower=lower)


@dataclass(frozen=True)
class LondonNyOverlapMomentum:
    name: str = "london_ny_overlap_momentum"
    session_start: str = "08:00"
    session_end: str = "12:00"
    lookback: int = 12
    atr_period: int = 14
    max_spread: int | None = None
    news_blackout: bool = False

    def generate_signal(
        self, candles: pd.DataFrame, current_index: int, *, has_position: bool = False
    ) -> NySessionSignalResult:
        filtered = _filter(self, candles, current_index, has_position)
        if filtered is not None:
            return filtered
        history = candles.iloc[: current_index + 1].copy()
        if len(history) < max(self.lookback + 1, self.atr_period):
            return NySessionSignalResult.wait("insufficient_history")
        channel = donchian_channel(history, self.lookback)
        close = float(history["close"].iloc[-1])
        atr = average_true_range(history, self.atr_period).iloc[-1]
        previous_upper = channel.upper.iloc[-2]
        previous_lower = channel.lower.iloc[-2]
        if pd.isna(atr) or pd.isna(previous_upper) or pd.isna(previous_lower):
            return NySessionSignalResult.wait("indicator_unavailable")
        if has_position and previous_lower < close < previous_upper:
            return NySessionSignalResult(signal=NySessionSignal.EXIT, reason="momentum_stalled")
        if close > float(previous_upper):
            return _entry(NySessionSignal.ENTER_LONG, close, close - float(atr) * 1.2)
        if close < float(previous_lower):
            return _entry(NySessionSignal.ENTER_SHORT, close, close + float(atr) * 1.2)
        return NySessionSignalResult.wait("no_overlap_momentum")


@dataclass(frozen=True)
class VolumeVolatilityExpansion:
    name: str = "volume_volatility_expansion"
    session_start: str = "08:00"
    session_end: str = "17:00"
    lookback: int = 20
    volume_multiple: float = 1.5
    range_multiple: float = 1.5
    max_spread: int | None = None
    news_blackout: bool = False

    def generate_signal(
        self, candles: pd.DataFrame, current_index: int, *, has_position: bool = False
    ) -> NySessionSignalResult:
        filtered = _filter(self, candles, current_index, has_position)
        if filtered is not None:
            return filtered
        history = candles.iloc[: current_index + 1].copy()
        if len(history) < self.lookback + 1:
            return NySessionSignalResult.wait("insufficient_history")
        recent = history.iloc[-self.lookback - 1 : -1]
        current = history.iloc[-1]
        avg_volume = float(recent["volume"].mean())
        avg_range = float((recent["high"] - recent["low"]).mean())
        current_range = float(current["high"] - current["low"])
        close = float(current["close"])
        open_price = float(current["open"])
        expanded = (
            float(current["volume"]) >= avg_volume * self.volume_multiple
            and current_range >= avg_range * self.range_multiple
        )
        if not expanded:
            return NySessionSignalResult.wait("no_volume_volatility_expansion")
        if close > open_price:
            return _entry(NySessionSignal.ENTER_LONG, close, float(current["low"]))
        if close < open_price:
            return _entry(NySessionSignal.ENTER_SHORT, close, float(current["high"]))
        return NySessionSignalResult.wait("neutral_expansion_candle")


STRATEGY_REGISTRY = {
    "opening_range_breakout": OpeningRangeBreakout,
    "vwap_trend_continuation": VwapTrendContinuation,
    "dynamic_noise_band_vwap": DynamicNoiseBandVwap,
    "london_ny_overlap_momentum": LondonNyOverlapMomentum,
    "volume_volatility_expansion": VolumeVolatilityExpansion,
}


def get_ny_session_strategy(name: str, params: dict[str, object] | None = None):
    try:
        strategy_type = STRATEGY_REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"unknown NY-session strategy: {name}") from exc
    return strategy_type(**(params or {}))


def _filter(
    strategy: SessionStrategy,
    candles: pd.DataFrame,
    current_index: int,
    has_position: bool,
) -> NySessionSignalResult | None:
    session_filter = NySessionFilter(
        start=strategy.session_start,
        end=strategy.session_end,
        max_spread=strategy.max_spread,
        news_blackout=strategy.news_blackout,
    )
    return session_filter.check(candles, current_index, has_position=has_position)


def _entry(signal: NySessionSignal, entry_price: float, stop_loss: float) -> NySessionSignalResult:
    if signal == NySessionSignal.ENTER_LONG and stop_loss >= entry_price:
        return NySessionSignalResult.wait("invalid_long_stop")
    if signal == NySessionSignal.ENTER_SHORT and stop_loss <= entry_price:
        return NySessionSignalResult.wait("invalid_short_stop")
    return NySessionSignalResult(signal=signal, reason="strategy_setup", stop_loss=stop_loss)


def _exit_if_mean_reverted(close: float, middle: float) -> NySessionSignalResult:
    if close < middle:
        return NySessionSignalResult(signal=NySessionSignal.EXIT, reason="mean_reversion_exit")
    return NySessionSignalResult.wait("in_position")

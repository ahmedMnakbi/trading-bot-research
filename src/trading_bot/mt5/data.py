from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import import_module
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from trading_bot.data.validation import count_missing_candles, timeframe_to_timedelta
from trading_bot.mt5.timezone import epoch_seconds_to_utc, to_new_york_time

MT5_TIMEFRAME_NAMES: dict[str, str] = {
    "1m": "TIMEFRAME_M1",
    "5m": "TIMEFRAME_M5",
    "15m": "TIMEFRAME_M15",
    "30m": "TIMEFRAME_M30",
    "1h": "TIMEFRAME_H1",
    "4h": "TIMEFRAME_H4",
    "1d": "TIMEFRAME_D1",
}


class Mt5RatesError(RuntimeError):
    """Raised when read-only MT5 rates cannot be loaded."""


class Mt5RateBar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    new_york_timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    spread: int | None = Field(default=None, ge=0)
    real_volume: float | None = Field(default=None, ge=0)

    @field_validator("timestamp")
    @classmethod
    def require_utc_timestamp(cls, timestamp: datetime) -> datetime:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return timestamp.astimezone(UTC)

    @model_validator(mode="after")
    def validate_bounds(self) -> Mt5RateBar:
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("high must be greater than or equal to open, low, and close")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("low must be less than or equal to open, high, and close")
        if self.new_york_timestamp.tzinfo is None:
            raise ValueError("new_york_timestamp must be timezone-aware")
        return self


@dataclass(frozen=True)
class Mt5RatesQualityReport:
    rows: int
    first_timestamp: datetime | None
    last_timestamp: datetime | None
    missing_candle_count: int
    duplicate_count: int
    invalid_ohlcv_row_count: int
    latest_incomplete: bool
    sorted_ascending: bool
    max_spread: int | None


class Mt5RatesProvider:
    def __init__(self, mt5_module: Any | None = None) -> None:
        self._mt5 = mt5_module

    def fetch_rates(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[Mt5RateBar]:
        module = self._module()
        mt5_timeframe = _mt5_timeframe(module, timeframe)
        try:
            raw_rates = module.copy_rates_range(
                symbol,
                mt5_timeframe,
                start.astimezone(UTC),
                end.astimezone(UTC),
            )
        except AttributeError as exc:
            raise Mt5RatesError("MetaTrader5 package does not expose historical rates") from exc
        if raw_rates is None:
            raise Mt5RatesError("MT5 historical rates request returned no data")
        return rates_to_bars(raw_rates)

    def fetch_recent_rates(
        self,
        *,
        symbol: str,
        timeframe: str,
        count: int,
    ) -> list[Mt5RateBar]:
        if count < 1:
            raise ValueError("count must be at least 1")
        module = self._module()
        mt5_timeframe = _mt5_timeframe(module, timeframe)
        try:
            raw_rates = module.copy_rates_from_pos(symbol, mt5_timeframe, 0, count)
        except AttributeError as exc:
            raise Mt5RatesError("MetaTrader5 package does not expose recent rates") from exc
        if raw_rates is None:
            raise Mt5RatesError("MT5 recent rates request returned no data")
        return rates_to_bars(raw_rates)

    def _module(self) -> Any:
        if self._mt5 is not None:
            return self._mt5
        try:
            self._mt5 = import_module("MetaTrader5")
        except ModuleNotFoundError as exc:
            raise Mt5RatesError("MetaTrader5 package is not installed") from exc
        return self._mt5


def rates_to_bars(raw_rates: Iterable[Any]) -> list[Mt5RateBar]:
    bars = [_rate_to_bar(raw) for raw in raw_rates]
    return sorted(bars, key=lambda bar: bar.timestamp)


def validate_mt5_bars(
    bars: Sequence[Mt5RateBar],
    timeframe: str,
    *,
    validate_continuity: bool = True,
) -> list[Mt5RateBar]:
    timestamps = [bar.timestamp for bar in bars]
    if len(timestamps) != len(set(timestamps)):
        raise ValueError("duplicate MT5 timestamps detected")
    if timestamps != sorted(timestamps):
        raise ValueError("MT5 rates must be sorted ascending")
    if validate_continuity and count_missing_candles(_as_ohlcv_like(bars), timeframe) > 0:
        raise ValueError("missing MT5 candle gaps detected")
    return list(bars)


def build_mt5_quality_report(
    bars: Sequence[Mt5RateBar],
    timeframe: str,
    *,
    now: datetime | None = None,
) -> Mt5RatesQualityReport:
    timestamps = [bar.timestamp for bar in bars]
    sorted_ascending = timestamps == sorted(timestamps)
    duplicate_count = len(timestamps) - len(set(timestamps))
    sorted_bars = sorted(bars, key=lambda bar: bar.timestamp)
    latest_incomplete = False
    if sorted_bars:
        latest_incomplete = (
            sorted_bars[-1].timestamp + timeframe_to_timedelta(timeframe)
            > (now or datetime.now(UTC)).astimezone(UTC)
        )
    spreads = [bar.spread for bar in bars if bar.spread is not None]
    return Mt5RatesQualityReport(
        rows=len(bars),
        first_timestamp=sorted_bars[0].timestamp if sorted_bars else None,
        last_timestamp=sorted_bars[-1].timestamp if sorted_bars else None,
        missing_candle_count=count_missing_candles(_as_ohlcv_like(sorted_bars), timeframe),
        duplicate_count=duplicate_count,
        invalid_ohlcv_row_count=0,
        latest_incomplete=latest_incomplete,
        sorted_ascending=sorted_ascending,
        max_spread=max(spreads) if spreads else None,
    )


def _rate_to_bar(raw: Any) -> Mt5RateBar:
    data = _raw_mapping(raw)
    timestamp = epoch_seconds_to_utc(data["time"])
    return Mt5RateBar(
        timestamp=timestamp,
        new_york_timestamp=to_new_york_time(timestamp),
        open=float(data["open"]),
        high=float(data["high"]),
        low=float(data["low"]),
        close=float(data["close"]),
        volume=float(data.get("tick_volume", data.get("volume", 0))),
        spread=_optional_int(data.get("spread")),
        real_volume=_optional_float(data.get("real_volume")),
    )


def _raw_mapping(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if hasattr(raw, "_asdict"):
        return raw._asdict()
    if hasattr(raw, "dtype") and getattr(raw.dtype, "names", None):
        return {
            name: raw[name].item() if hasattr(raw[name], "item") else raw[name]
            for name in raw.dtype.names
        }
    return vars(raw)


def _mt5_timeframe(module: Any, timeframe: str) -> Any:
    try:
        name = MT5_TIMEFRAME_NAMES[timeframe]
    except KeyError as exc:
        raise ValueError(f"unsupported MT5 timeframe: {timeframe}") from exc
    try:
        return getattr(module, name)
    except AttributeError as exc:
        raise Mt5RatesError(f"MetaTrader5 package missing timeframe constant: {name}") from exc


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)


def _as_ohlcv_like(bars: Sequence[Mt5RateBar]):
    from trading_bot.data.models import OhlcvCandle

    return [
        OhlcvCandle(
            timestamp=bar.timestamp,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
        )
        for bar in bars
    ]

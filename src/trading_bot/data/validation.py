from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from trading_bot.data.models import OhlcvCandle

TIMEFRAME_SECONDS: dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
    "1w": 604800,
}


@dataclass(frozen=True)
class DataQualityReport:
    rows: int
    first_timestamp: datetime | None
    last_timestamp: datetime | None
    missing_candle_count: int
    duplicate_count: int
    invalid_ohlcv_row_count: int
    latest_incomplete: bool
    sorted_ascending: bool


def timeframe_to_timedelta(timeframe: str) -> timedelta:
    try:
        return timedelta(seconds=TIMEFRAME_SECONDS[timeframe])
    except KeyError as exc:
        raise ValueError(f"unsupported timeframe: {timeframe}") from exc


def sort_and_deduplicate(candles: list[OhlcvCandle]) -> list[OhlcvCandle]:
    by_timestamp: dict[datetime, OhlcvCandle] = {}
    for candle in candles:
        by_timestamp[candle.timestamp] = candle
    return [by_timestamp[timestamp] for timestamp in sorted(by_timestamp)]


def drop_partial_latest_candle(
    candles: list[OhlcvCandle], timeframe: str, *, now: datetime | None = None
) -> list[OhlcvCandle]:
    if not candles:
        return []
    current_time = (now or datetime.now(UTC)).astimezone(UTC)
    interval = timeframe_to_timedelta(timeframe)
    sorted_candles = sorted(candles, key=lambda candle: candle.timestamp)
    latest = sorted_candles[-1]
    if latest.timestamp + interval > current_time:
        return sorted_candles[:-1]
    return sorted_candles


def count_missing_candles(candles: list[OhlcvCandle], timeframe: str) -> int:
    if len(candles) < 2:
        return 0
    interval = timeframe_to_timedelta(timeframe)
    missing = 0
    sorted_candles = sorted(candles, key=lambda candle: candle.timestamp)
    for previous, current in zip(sorted_candles, sorted_candles[1:], strict=False):
        gap = current.timestamp - previous.timestamp
        if gap > interval:
            missing += int(gap / interval) - 1
    return missing


def build_quality_report(
    candles: list[OhlcvCandle], timeframe: str, *, now: datetime | None = None
) -> DataQualityReport:
    timestamps = [candle.timestamp for candle in candles]
    sorted_ascending = timestamps == sorted(timestamps)
    duplicate_count = len(timestamps) - len(set(timestamps))
    sorted_candles = sorted(candles, key=lambda candle: candle.timestamp)
    latest_incomplete = False
    if sorted_candles:
        latest_incomplete = (
            sorted_candles[-1].timestamp + timeframe_to_timedelta(timeframe)
            > (now or datetime.now(UTC)).astimezone(UTC)
        )
    return DataQualityReport(
        rows=len(candles),
        first_timestamp=sorted_candles[0].timestamp if sorted_candles else None,
        last_timestamp=sorted_candles[-1].timestamp if sorted_candles else None,
        missing_candle_count=count_missing_candles(sorted_candles, timeframe),
        duplicate_count=duplicate_count,
        invalid_ohlcv_row_count=0,
        latest_incomplete=latest_incomplete,
        sorted_ascending=sorted_ascending,
    )


def validate_candles(
    candles: list[OhlcvCandle],
    timeframe: str,
    *,
    validate_continuity: bool = True,
) -> list[OhlcvCandle]:
    timestamps = [candle.timestamp for candle in candles]
    if len(timestamps) != len(set(timestamps)):
        raise ValueError("duplicate timestamps detected")
    if timestamps != sorted(timestamps):
        raise ValueError("candles must be sorted ascending")
    if validate_continuity and count_missing_candles(candles, timeframe) > 0:
        raise ValueError("missing candle gaps detected")
    return candles

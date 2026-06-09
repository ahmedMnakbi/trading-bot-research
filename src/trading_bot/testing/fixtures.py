from __future__ import annotations

from datetime import UTC, datetime, timedelta


def base_timestamp() -> datetime:
    return datetime(2024, 1, 1, tzinfo=UTC)


def synthetic_candle_times(
    count: int = 3,
    *,
    duplicate: bool = False,
    gap: bool = False,
) -> list[str]:
    start = base_timestamp()
    times = [start + timedelta(hours=4 * index) for index in range(count)]
    if duplicate and len(times) > 1:
        times[1] = times[0]
    if gap and len(times) > 2:
        times[2] = times[1] + timedelta(hours=12)
    return [timestamp.isoformat() for timestamp in times]

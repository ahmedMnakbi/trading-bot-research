from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

NEW_YORK_TIMEZONE = "America/New_York"


def broker_time_to_utc(timestamp: datetime, broker_timezone: str) -> datetime:
    broker_zone = ZoneInfo(broker_timezone)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        timestamp = timestamp.replace(tzinfo=broker_zone)
    return timestamp.astimezone(UTC)


def epoch_seconds_to_utc(timestamp_seconds: int | float) -> datetime:
    return datetime.fromtimestamp(timestamp_seconds, tz=UTC)


def to_new_york_time(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return timestamp.astimezone(ZoneInfo(NEW_YORK_TIMEZONE))


def session_utc_window(
    session_date: date,
    *,
    start: str,
    end: str,
    timezone: str = NEW_YORK_TIMEZONE,
) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone)
    start_time = _parse_hhmm(start)
    end_time = _parse_hhmm(end)
    start_local = datetime.combine(session_date, start_time, tzinfo=zone)
    end_local = datetime.combine(session_date, end_time, tzinfo=zone)
    if end_local <= start_local:
        end_local += timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def is_in_session(
    timestamp: datetime,
    *,
    start: str,
    end: str,
    timezone: str = NEW_YORK_TIMEZONE,
) -> bool:
    local_timestamp = to_new_york_time(timestamp).astimezone(ZoneInfo(timezone))
    session_start, session_end = session_utc_window(
        local_timestamp.date(),
        start=start,
        end=end,
        timezone=timezone,
    )
    timestamp_utc = timestamp.astimezone(UTC)
    return session_start <= timestamp_utc < session_end


def _parse_hhmm(value: str) -> time:
    try:
        hour_text, minute_text = value.split(":", maxsplit=1)
        return time(hour=int(hour_text), minute=int(minute_text))
    except ValueError as exc:
        raise ValueError(f"invalid session time: {value}") from exc

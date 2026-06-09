from datetime import UTC, date, datetime

from trading_bot.mt5.timezone import broker_time_to_utc, is_in_session, session_utc_window


def test_new_york_session_utc_window_uses_est_offset() -> None:
    start, end = session_utc_window(date(2026, 1, 15), start="08:00", end="17:00")

    assert start == datetime(2026, 1, 15, 13, 0, tzinfo=UTC)
    assert end == datetime(2026, 1, 15, 22, 0, tzinfo=UTC)


def test_new_york_session_utc_window_uses_edt_offset() -> None:
    start, end = session_utc_window(date(2026, 7, 15), start="08:00", end="17:00")

    assert start == datetime(2026, 7, 15, 12, 0, tzinfo=UTC)
    assert end == datetime(2026, 7, 15, 21, 0, tzinfo=UTC)


def test_broker_time_to_utc_converts_naive_broker_timestamp() -> None:
    timestamp = broker_time_to_utc(datetime(2026, 1, 15, 8, 0), "America/New_York")

    assert timestamp == datetime(2026, 1, 15, 13, 0, tzinfo=UTC)


def test_is_in_session_is_dst_aware() -> None:
    assert is_in_session(datetime(2026, 7, 15, 13, 0, tzinfo=UTC), start="08:00", end="17:00")
    assert not is_in_session(
        datetime(2026, 7, 15, 22, 0, tzinfo=UTC),
        start="08:00",
        end="17:00",
    )

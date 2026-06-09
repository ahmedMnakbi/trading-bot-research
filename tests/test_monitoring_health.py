from __future__ import annotations

from trading_bot.monitoring.health import health_event


def test_health_event_marks_live_trading_false() -> None:
    event = health_event("DATA_EMPTY", "empty")

    assert event["code"] == "DATA_EMPTY"
    assert event["live_trading"] is False


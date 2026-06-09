from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from trading_bot.data.models import OhlcvCandle
from trading_bot.data.validation import build_quality_report, sort_and_deduplicate, validate_candles


def candle_at(timestamp: datetime) -> OhlcvCandle:
    return OhlcvCandle(
        timestamp=timestamp,
        open=100,
        high=110,
        low=90,
        close=105,
        volume=1,
    )


def test_validation_detects_duplicate_timestamps() -> None:
    timestamp = datetime(2024, 1, 1, tzinfo=UTC)

    with pytest.raises(ValueError, match="duplicate"):
        validate_candles([candle_at(timestamp), candle_at(timestamp)], "4h")


def test_validation_detects_missing_candles() -> None:
    candles = [
        candle_at(datetime(2024, 1, 1, tzinfo=UTC)),
        candle_at(datetime(2024, 1, 1, 8, tzinfo=UTC)),
    ]

    with pytest.raises(ValueError, match="missing"):
        validate_candles(candles, "4h")

    report = build_quality_report(candles, "4h", now=datetime(2024, 1, 2, tzinfo=UTC))
    assert report.missing_candle_count == 1


def test_validation_sorts_or_rejects_unsorted_data() -> None:
    later = candle_at(datetime(2024, 1, 1, 4, tzinfo=UTC))
    earlier = candle_at(datetime(2024, 1, 1, tzinfo=UTC))

    with pytest.raises(ValueError, match="sorted"):
        validate_candles([later, earlier], "4h")

    assert sort_and_deduplicate([later, earlier]) == [earlier, later]


def test_quality_report_detects_latest_incomplete() -> None:
    now = datetime(2024, 1, 1, 5, tzinfo=UTC)
    candles = [candle_at(now - timedelta(hours=1))]

    report = build_quality_report(candles, "4h", now=now)

    assert report.latest_incomplete is True


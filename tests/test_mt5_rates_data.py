from datetime import UTC, datetime

import pytest

from trading_bot.mt5.data import (
    Mt5RatesProvider,
    build_mt5_quality_report,
    rates_to_bars,
    validate_mt5_bars,
)


class FakeMt5:
    TIMEFRAME_M5 = "M5"

    def __init__(self) -> None:
        self.calls: list[tuple[str, object, datetime, datetime]] = []
        self.recent_calls: list[tuple[str, object, int, int]] = []

    def copy_rates_range(
        self,
        symbol: str,
        timeframe: object,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, float | int]]:
        self.calls.append((symbol, timeframe, start, end))
        return [
            {
                "time": int(datetime(2026, 1, 1, 13, 0, tzinfo=UTC).timestamp()),
                "open": 100.0,
                "high": 102.0,
                "low": 99.0,
                "close": 101.0,
                "tick_volume": 10,
                "spread": 12,
                "real_volume": 0,
            },
            {
                "time": int(datetime(2026, 1, 1, 13, 5, tzinfo=UTC).timestamp()),
                "open": 101.0,
                "high": 103.0,
                "low": 100.0,
                "close": 102.0,
                "tick_volume": 11,
                "spread": 14,
                "real_volume": 0,
            },
        ]

    def copy_rates_from_pos(
        self,
        symbol: str,
        timeframe: object,
        start_pos: int,
        count: int,
    ) -> list[dict[str, float | int]]:
        self.recent_calls.append((symbol, timeframe, start_pos, count))
        return [
            {
                "time": int(datetime(2026, 1, 1, 13, 10, tzinfo=UTC).timestamp()),
                "open": 102.0,
                "high": 104.0,
                "low": 101.0,
                "close": 103.0,
                "tick_volume": 12,
                "spread": 16,
                "real_volume": 0,
            }
        ]


def test_mt5_rates_provider_fetches_readonly_historical_rates() -> None:
    fake = FakeMt5()
    provider = Mt5RatesProvider(mt5_module=fake)

    bars = provider.fetch_rates(
        symbol="EURUSD",
        timeframe="5m",
        start=datetime(2026, 1, 1, 13, 0, tzinfo=UTC),
        end=datetime(2026, 1, 1, 14, 0, tzinfo=UTC),
    )

    assert len(bars) == 2
    assert fake.calls[0][0] == "EURUSD"
    assert fake.calls[0][1] == "M5"
    assert bars[0].timestamp == datetime(2026, 1, 1, 13, 0, tzinfo=UTC)
    assert bars[0].new_york_timestamp.hour == 8
    assert bars[1].spread == 14


def test_mt5_rates_provider_fetches_readonly_recent_rates() -> None:
    fake = FakeMt5()
    provider = Mt5RatesProvider(mt5_module=fake)

    bars = provider.fetch_recent_rates(symbol="EURUSD", timeframe="5m", count=25)

    assert len(bars) == 1
    assert fake.recent_calls == [("EURUSD", "M5", 0, 25)]
    assert bars[0].timestamp == datetime(2026, 1, 1, 13, 10, tzinfo=UTC)
    assert bars[0].spread == 16


def test_mt5_rates_validation_detects_duplicate_timestamps() -> None:
    bars = rates_to_bars(
        [
            {
                "time": int(datetime(2026, 1, 1, 13, 0, tzinfo=UTC).timestamp()),
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100,
                "tick_volume": 1,
            },
            {
                "time": int(datetime(2026, 1, 1, 13, 0, tzinfo=UTC).timestamp()),
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100,
                "tick_volume": 1,
            },
        ]
    )

    with pytest.raises(ValueError, match="duplicate"):
        validate_mt5_bars(bars, "5m")


def test_mt5_rates_quality_report_counts_missing_and_spread() -> None:
    bars = rates_to_bars(
        [
            {
                "time": int(datetime(2026, 1, 1, 13, 0, tzinfo=UTC).timestamp()),
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100,
                "tick_volume": 1,
                "spread": 10,
            },
            {
                "time": int(datetime(2026, 1, 1, 13, 10, tzinfo=UTC).timestamp()),
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100,
                "tick_volume": 1,
                "spread": 20,
            },
        ]
    )

    report = build_mt5_quality_report(
        bars,
        "5m",
        now=datetime(2026, 1, 1, 14, 0, tzinfo=UTC),
    )

    assert report.rows == 2
    assert report.missing_candle_count == 1
    assert report.max_spread == 20

from datetime import UTC, datetime

from trading_bot.mt5.cache import Mt5RatesCache
from trading_bot.mt5.data import rates_to_bars


def test_mt5_rates_cache_writes_reads_and_inspects(tmp_path) -> None:
    cache = Mt5RatesCache(tmp_path)
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
                "time": int(datetime(2026, 1, 1, 13, 5, tzinfo=UTC).timestamp()),
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 101,
                "tick_volume": 2,
                "spread": 11,
            },
        ]
    )

    merged = cache.merge_and_write("demo_broker", "EURUSD", "5m", bars)
    loaded = cache.read("demo_broker", "EURUSD", "5m")
    report = cache.inspect("demo_broker", "EURUSD", "5m")

    assert len(merged) == 2
    assert loaded[0].new_york_timestamp.hour == 8
    assert report["rows"] == 2
    assert report["duplicate_count"] == 0
    assert report["missing_candle_count"] == 0
    assert cache.path_for("demo_broker", "EURUSD", "5m").exists()
    assert cache.metadata_path_for("demo_broker", "EURUSD", "5m").exists()

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from trading_bot.data.cache import OhlcvCache
from trading_bot.data.models import OhlcvCandle


def candle_at(timestamp: datetime, close: float = 105) -> OhlcvCandle:
    return OhlcvCandle(
        timestamp=timestamp,
        open=100,
        high=110,
        low=90,
        close=close,
        volume=1,
    )


def test_cache_roundtrip_parquet(tmp_path) -> None:  # type: ignore[no-untyped-def]
    cache = OhlcvCache(tmp_path)
    candles = [candle_at(datetime(2024, 1, 1, tzinfo=UTC))]

    cache.merge_and_write("kraken", "BTC/USDT", "4h", candles)

    assert cache.read("kraken", "BTC/USDT", "4h") == candles
    assert cache.metadata_path_for("kraken", "BTC/USDT", "4h").exists()


def test_cache_merge_deduplicates_by_timestamp(tmp_path) -> None:  # type: ignore[no-untyped-def]
    cache = OhlcvCache(tmp_path)
    timestamp = datetime(2024, 1, 1, tzinfo=UTC)
    cache.merge_and_write("kraken", "BTC/USDT", "4h", [candle_at(timestamp, close=100)])

    merged = cache.merge_and_write("kraken", "BTC/USDT", "4h", [candle_at(timestamp, close=101)])

    assert len(merged) == 1
    assert merged[0].close == 101


def test_cache_does_not_overwrite_with_empty_dataset(tmp_path) -> None:  # type: ignore[no-untyped-def]
    cache = OhlcvCache(tmp_path)

    with pytest.raises(ValueError, match="empty"):
        cache.merge_and_write("kraken", "BTC/USDT", "4h", [])

    candle = candle_at(datetime(2024, 1, 1, tzinfo=UTC))
    cache.merge_and_write("kraken", "BTC/USDT", "4h", [candle])

    assert cache.merge_and_write("kraken", "BTC/USDT", "4h", []) == [candle]


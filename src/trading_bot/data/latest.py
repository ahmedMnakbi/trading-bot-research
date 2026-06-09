from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trading_bot.data.models import OhlcvCandle
from trading_bot.data.provider import MarketDataProvider
from trading_bot.data.validation import drop_partial_latest_candle, validate_candles


def fetch_latest_public_ohlcv(
    *,
    provider: MarketDataProvider,
    symbol: str,
    timeframe: str,
    limit: int,
    allow_partial_latest_candle: bool,
) -> list[OhlcvCandle]:
    since_ms = int((datetime.now(UTC) - timedelta(days=30)).timestamp() * 1000)
    candles = provider.fetch_ohlcv(symbol, timeframe, since_ms, limit)
    candles = sorted(candles, key=lambda candle: candle.timestamp)
    if not allow_partial_latest_candle:
        candles = drop_partial_latest_candle(candles, timeframe)
    validate_candles(candles, timeframe, validate_continuity=False)
    return candles

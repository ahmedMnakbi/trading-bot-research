from __future__ import annotations

from typing import Protocol

from trading_bot.data.models import OhlcvCandle


class MarketDataProvider(Protocol):
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since_ms: int,
        limit: int,
    ) -> list[OhlcvCandle]:
        """Fetch read-only public OHLCV candles."""


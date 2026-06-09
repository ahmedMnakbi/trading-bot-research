from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import ccxt
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from trading_bot.data.models import OhlcvCandle


class MarketDataError(RuntimeError):
    """Raised when read-only market data cannot be fetched."""


class CcxtOhlcvProvider:
    def __init__(
        self,
        exchange_id: str,
        *,
        timeout_seconds: int = 30,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 2,
    ) -> None:
        if not hasattr(ccxt, exchange_id):
            raise MarketDataError(f"unsupported exchange: {exchange_id}")

        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class(
            {
                "enableRateLimit": True,
                "timeout": timeout_seconds * 1000,
            }
        )
        self.exchange_id = exchange_id
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds
        self._reject_private_configuration()

    def _reject_private_configuration(self) -> None:
        for key in ("apiKey", "secret", "password", "uid"):
            if getattr(self.exchange, key, None):
                raise MarketDataError("private authenticated exchange configuration is prohibited")

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since_ms: int,
        limit: int,
    ) -> list[OhlcvCandle]:
        @retry(
            reraise=True,
            stop=stop_after_attempt(self.retry_attempts),
            wait=wait_fixed(self.retry_backoff_seconds),
            retry=retry_if_exception_type((ccxt.NetworkError, ccxt.RateLimitExceeded)),
        )
        def _fetch() -> list[Any]:
            if not self.exchange.has.get("fetchOHLCV"):
                raise MarketDataError(f"exchange does not support OHLCV: {self.exchange_id}")
            return self.exchange.fetch_ohlcv(symbol, timeframe, since_ms, limit)

        try:
            raw_candles = _fetch()
        except ccxt.BadSymbol as exc:
            raise MarketDataError(f"unsupported symbol: {symbol}") from exc
        except ccxt.BadRequest as exc:
            raise MarketDataError(f"unsupported timeframe or request: {timeframe}") from exc
        except ccxt.RateLimitExceeded as exc:
            raise MarketDataError("exchange rate limit exceeded") from exc
        except ccxt.NetworkError as exc:
            raise MarketDataError("network error while fetching OHLCV") from exc

        if not raw_candles:
            raise MarketDataError("empty OHLCV response")
        return [self._parse_raw_candle(raw_candle) for raw_candle in raw_candles]

    @staticmethod
    def _parse_raw_candle(raw_candle: Any) -> OhlcvCandle:
        if not isinstance(raw_candle, list | tuple) or len(raw_candle) < 6:
            raise MarketDataError("malformed OHLCV response")
        timestamp_ms, open_, high, low, close, volume = raw_candle[:6]
        return OhlcvCandle(
            timestamp=datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC),
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume,
        )


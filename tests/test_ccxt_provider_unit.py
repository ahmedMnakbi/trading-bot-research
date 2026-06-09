from __future__ import annotations

from typing import Any

import ccxt
import pytest

from trading_bot.data.ccxt_provider import CcxtOhlcvProvider, MarketDataError


class FakePublicExchange:
    captured_config: dict[str, Any] = {}

    def __init__(self, config: dict[str, Any]) -> None:
        self.__class__.captured_config = config
        self.has = {"fetchOHLCV": True}
        self.apiKey = None
        self.secret = None
        self.password = None
        self.uid = None

    def fetch_ohlcv(
        self, symbol: str, timeframe: str, since_ms: int, limit: int
    ) -> list[list[float]]:
        return [[1704067200000, 100, 110, 90, 105, 1]]


class FakePrivateExchange(FakePublicExchange):
    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.apiKey = "not-allowed"


def test_ccxt_provider_uses_enable_rate_limit_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ccxt, "fakepublic", FakePublicExchange, raising=False)

    provider = CcxtOhlcvProvider("fakepublic")
    candles = provider.fetch_ohlcv("BTC/USDT", "4h", 1704067200000, 500)

    assert FakePublicExchange.captured_config["enableRateLimit"] is True
    assert FakePublicExchange.captured_config["timeout"] == 30000
    assert len(candles) == 1


def test_ccxt_provider_rejects_private_endpoint_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ccxt, "fakeprivate", FakePrivateExchange, raising=False)

    with pytest.raises(MarketDataError, match="private"):
        CcxtOhlcvProvider("fakeprivate")


from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from trading_bot.data.models import OhlcvCandle


def test_valid_ohlcv_candle_accepts_utc_timestamp() -> None:
    candle = OhlcvCandle(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        open=100,
        high=110,
        low=90,
        close=105,
        volume=12,
    )

    assert candle.timestamp.tzinfo == UTC


def test_ohlcv_candle_rejects_negative_price() -> None:
    with pytest.raises(ValidationError):
        OhlcvCandle(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            open=-100,
            high=110,
            low=90,
            close=105,
            volume=12,
        )


def test_ohlcv_candle_rejects_negative_volume() -> None:
    with pytest.raises(ValidationError):
        OhlcvCandle(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            open=100,
            high=110,
            low=90,
            close=105,
            volume=-1,
        )


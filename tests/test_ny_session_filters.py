from datetime import UTC, datetime, timedelta

import pandas as pd

from trading_bot.ny_session.filters import NySessionFilter
from trading_bot.ny_session.models import NySessionSignal


def _candles(timestamp: datetime, *, spread: int = 10) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timestamp": timestamp,
                "new_york_timestamp": timestamp.astimezone().isoformat(),
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100,
                "volume": 100,
                "spread": spread,
            }
        ]
    )


def test_filter_blocks_signal_outside_session() -> None:
    candles = _candles(datetime(2026, 7, 15, 22, 0, tzinfo=UTC))

    result = NySessionFilter(start="08:00", end="17:00").check(candles, 0)

    assert result is not None
    assert result.signal == NySessionSignal.WAIT
    assert result.reason == "outside_configured_session"


def test_filter_emits_session_close_for_open_position() -> None:
    candles = _candles(datetime(2026, 7, 15, 22, 0, tzinfo=UTC))

    result = NySessionFilter(start="08:00", end="17:00").check(candles, 0, has_position=True)

    assert result is not None
    assert result.signal == NySessionSignal.SESSION_CLOSE


def test_filter_blocks_high_spread_and_news() -> None:
    candles = _candles(datetime(2026, 7, 15, 13, 0, tzinfo=UTC), spread=50)

    spread_result = NySessionFilter(start="08:00", end="17:00", max_spread=20).check(candles, 0)
    news_result = NySessionFilter(start="08:00", end="17:00", news_blackout=True).check(
        candles,
        0,
    )

    assert spread_result is not None
    assert spread_result.signal == NySessionSignal.SKIP_SPREAD
    assert news_result is not None
    assert news_result.signal == NySessionSignal.SKIP_NEWS


def test_filter_allows_in_session_conditions() -> None:
    timestamp = datetime(2026, 7, 15, 12, 30, tzinfo=UTC) + timedelta(minutes=0)
    candles = _candles(timestamp)

    assert NySessionFilter(start="08:00", end="17:00", max_spread=20).check(candles, 0) is None

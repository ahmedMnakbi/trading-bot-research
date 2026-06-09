from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from trading_bot.backtesting.events import Signal
from trading_bot.portfolio.account import AccountState
from trading_bot.strategies.buy_and_hold import BuyAndHoldStrategy
from trading_bot.strategies.noop import NoopStrategy


def test_noop_strategy_returns_hold() -> None:
    signal = NoopStrategy().generate_signal(pd.DataFrame(), 0, AccountState(cash=100))

    assert signal == Signal.HOLD


def test_strategy_cannot_access_future_candles_through_official_interface() -> None:
    candles = pd.DataFrame(
        {
            "timestamp": [
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 2, tzinfo=UTC),
                datetime(2024, 1, 3, tzinfo=UTC),
            ],
            "close": [100, 200, 300],
        }
    )
    visible = candles.iloc[:1].copy()

    assert len(visible) == 1
    assert BuyAndHoldStrategy().generate_signal(visible, 0, AccountState(cash=100)) == Signal.BUY


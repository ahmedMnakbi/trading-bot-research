from __future__ import annotations

import pandas as pd

from trading_bot.portfolio.account import AccountState
from trading_bot.portfolio.position import Position
from trading_bot.strategies.ema_trend import EmaTrendStrategy


def ema_fixture() -> pd.DataFrame:
    closes = [100] * 10 + [99, 101, 103, 105, 107, 109]
    return pd.DataFrame(
        {
            "high": [close + 2 for close in closes],
            "low": [close - 2 for close in closes],
            "close": closes,
        }
    )


def test_ema_strategy_emits_no_signal_before_enough_candles() -> None:
    strategy = EmaTrendStrategy(ema_fast=3, ema_slow=8, atr_period=3)

    intent = strategy.generate_signal(ema_fixture().iloc[:5], 4, AccountState(cash=1000))

    assert intent.action == "HOLD"


def test_ema_strategy_emits_buy_with_stop_loss_in_valid_trend_condition() -> None:
    strategy = EmaTrendStrategy(ema_fast=3, ema_slow=8, atr_period=3)

    candles = ema_fixture().iloc[:12]
    intent = strategy.generate_signal(candles, 11, AccountState(cash=1000))

    assert intent.action == "BUY"
    assert intent.stop_loss is not None


def test_ema_strategy_emits_exit_when_trend_fails() -> None:
    strategy = EmaTrendStrategy(ema_fast=3, ema_slow=8, atr_period=3)
    candles = ema_fixture()
    candles.loc[len(candles) - 1, "close"] = 90
    account = AccountState(cash=1000, position=Position("BTC/USDT", 1, 100))

    intent = strategy.generate_signal(candles, len(candles) - 1, account)

    assert intent.action == "EXIT"

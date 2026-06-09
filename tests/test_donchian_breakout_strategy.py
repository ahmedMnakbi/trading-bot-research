from __future__ import annotations

import pandas as pd

from trading_bot.portfolio.account import AccountState
from trading_bot.portfolio.position import Position
from trading_bot.strategies.donchian_breakout import DonchianBreakoutStrategy


def donchian_fixture(*, breakout: bool = True, exit_break: bool = False) -> pd.DataFrame:
    rows = []
    for _index in range(22):
        rows.append({"high": 100, "low": 90, "close": 95})
    rows[-1]["close"] = 105 if breakout else 99
    if exit_break:
        rows[-1]["close"] = 80
    return pd.DataFrame(rows)


def test_donchian_strategy_emits_no_signal_before_enough_candles() -> None:
    strategy = DonchianBreakoutStrategy(donchian_lookback=20, atr_period=14)
    intent = strategy.generate_signal(donchian_fixture().iloc[:10], 9, AccountState(cash=1000))

    assert intent.action == "HOLD"


def test_donchian_strategy_emits_buy_with_stop_loss_on_valid_breakout() -> None:
    strategy = DonchianBreakoutStrategy(donchian_lookback=20, atr_period=14)
    intent = strategy.generate_signal(donchian_fixture(), 21, AccountState(cash=1000))

    assert intent.action == "BUY"
    assert intent.stop_loss is not None
    assert intent.stop_loss < 105


def test_donchian_strategy_emits_exit_when_close_breaks_below_middle_channel() -> None:
    strategy = DonchianBreakoutStrategy(donchian_lookback=20, atr_period=14)
    account = AccountState(cash=1000, position=Position("BTC/USDT", 1, 100))
    intent = strategy.generate_signal(donchian_fixture(exit_break=True), 21, account)

    assert intent.action == "EXIT"

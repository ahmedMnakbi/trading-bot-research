from __future__ import annotations

import pandas as pd

from trading_bot.backtesting.events import TradeIntent
from trading_bot.portfolio.account import AccountState


class BuyAndHoldStrategy:
    name = "buy_and_hold"

    def generate_signal(
        self, candles: pd.DataFrame, current_index: int, account: AccountState
    ) -> TradeIntent:
        if current_index == 0 and account.position is None:
            close = float(candles["close"].iloc[-1])
            return TradeIntent(
                action="BUY",
                reason="strategy_entry",
                stop_loss=close * 0.95,
            )
        if current_index == len(candles) - 2 and account.position is not None:
            return TradeIntent(action="EXIT", reason="strategy_exit")
        return TradeIntent.hold("hold")

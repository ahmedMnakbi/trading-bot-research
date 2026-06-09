from __future__ import annotations

import pandas as pd

from trading_bot.backtesting.events import TradeIntent
from trading_bot.portfolio.account import AccountState


class NoopStrategy:
    name = "noop"

    def generate_signal(
        self, candles: pd.DataFrame, current_index: int, account: AccountState
    ) -> TradeIntent:
        return TradeIntent.hold("noop")

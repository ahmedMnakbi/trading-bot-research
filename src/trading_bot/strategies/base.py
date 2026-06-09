from __future__ import annotations

from typing import Protocol

import pandas as pd

from trading_bot.backtesting.events import TradeIntent
from trading_bot.portfolio.account import AccountState


class Strategy(Protocol):
    name: str

    def generate_signal(
        self,
        candles: pd.DataFrame,
        current_index: int,
        account: AccountState,
    ) -> TradeIntent:
        """Return a signal using only candles through current_index."""


def get_strategy(name: str, params: dict[str, object] | None = None) -> Strategy:
    from trading_bot.strategies.registry import get_strategy as registry_get_strategy

    return registry_get_strategy(name, params=params)

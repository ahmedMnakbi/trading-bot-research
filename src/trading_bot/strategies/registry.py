from __future__ import annotations

from trading_bot.strategies.base import Strategy
from trading_bot.strategies.buy_and_hold import BuyAndHoldStrategy
from trading_bot.strategies.donchian_breakout import DonchianBreakoutStrategy
from trading_bot.strategies.ema_trend import EmaTrendStrategy
from trading_bot.strategies.noop import NoopStrategy


def get_strategy(name: str, params: dict[str, object] | None = None) -> Strategy:
    strategy_params = params or {}
    strategies: dict[str, Strategy] = {
        "noop": NoopStrategy(),
        "buy_and_hold": BuyAndHoldStrategy(),
        "donchian_breakout": DonchianBreakoutStrategy.from_params(strategy_params),
        "ema_trend": EmaTrendStrategy.from_params(strategy_params),
    }
    try:
        return strategies[name]
    except KeyError as exc:
        raise ValueError(f"unsupported strategy: {name}") from exc

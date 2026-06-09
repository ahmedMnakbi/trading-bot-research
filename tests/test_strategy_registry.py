from __future__ import annotations

from trading_bot.strategies.registry import get_strategy


def test_strategy_registry_loads_all_baseline_strategies() -> None:
    assert get_strategy("noop").name == "noop"
    assert get_strategy("buy_and_hold").name == "buy_and_hold"
    assert get_strategy("donchian_breakout").name == "donchian_breakout"
    assert get_strategy("ema_trend").name == "ema_trend"


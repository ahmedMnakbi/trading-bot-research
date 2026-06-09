from __future__ import annotations

from trading_bot.backtesting.events import OrderSide


def apply_slippage(price: float, side: OrderSide, slippage_bps: float) -> tuple[float, float]:
    if slippage_bps < 0:
        raise ValueError("slippage_bps must be non-negative")
    adjustment = price * slippage_bps / 10_000
    if side == OrderSide.BUY:
        return price + adjustment, adjustment
    return price - adjustment, adjustment


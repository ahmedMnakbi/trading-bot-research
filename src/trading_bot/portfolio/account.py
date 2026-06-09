from __future__ import annotations

from dataclasses import dataclass

from trading_bot.portfolio.position import Position


@dataclass(frozen=True)
class AccountState:
    cash: float
    realized_pnl: float = 0
    unrealized_pnl: float = 0
    position: Position | None = None
    fees_paid: float = 0
    slippage_paid_estimate: float = 0
    equity: float | None = None

    def total_equity(self, mark_price: float | None = None) -> float:
        if self.equity is not None and mark_price is None:
            return self.equity
        if self.position is None:
            return self.cash
        price = mark_price if mark_price is not None else self.position.entry_price
        return self.cash + self.position.quantity * price


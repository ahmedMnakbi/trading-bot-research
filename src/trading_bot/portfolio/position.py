from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: float
    entry_price: float
    stop_loss: float | None = None
    take_profit: float | None = None

    @property
    def is_open(self) -> bool:
        return self.quantity > 0

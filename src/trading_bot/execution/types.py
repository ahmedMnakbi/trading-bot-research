from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from trading_bot.backtesting.events import OrderRequest, OrderSide, OrderStatus


@dataclass(frozen=True)
class ExecutionOrderRequest:
    symbol: str
    side: OrderSide
    quantity: float
    requested_price: float
    timestamp: datetime
    stop_loss: float | None = None
    take_profit: float | None = None
    reason: str = "strategy_entry"
    leverage: float = 1
    real_order: bool = False


@dataclass(frozen=True)
class OrderResult:
    symbol: str
    side: OrderSide
    quantity: float
    requested_price: float
    fill_price: float | None
    status: OrderStatus
    reason: str | None
    fee: float = 0
    slippage_paid_estimate: float = 0
    metadata: dict[str, object] = field(default_factory=dict)


class ExecutionClient(Protocol):
    def submit_order(self, order_request: OrderRequest) -> OrderResult:
        """Submit an order through the configured execution layer."""


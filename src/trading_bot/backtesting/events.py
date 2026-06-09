from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class Signal(StrEnum):
    HOLD = "HOLD"
    BUY = "BUY"
    SELL = "SELL"
    EXIT = "EXIT"


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(StrEnum):
    FILLED = "FILLED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: OrderSide
    quantity: float
    stop_loss: float | None = None
    take_profit: float | None = None
    reason: str = "strategy_entry"
    leverage: float = 1


@dataclass(frozen=True)
class OrderRecord:
    timestamp: datetime
    symbol: str
    side: OrderSide
    quantity: float
    requested_price: float
    fill_price: float | None
    status: OrderStatus
    reason: str | None
    fee: float = 0
    slippage_paid_estimate: float = 0


@dataclass(frozen=True)
class TradeRecord:
    entry_timestamp: datetime
    exit_timestamp: datetime
    symbol: str
    quantity: float
    entry_price: float
    exit_price: float
    pnl: float
    fees: float
    reason: str


class TradeIntent(BaseModel):
    action: Literal["HOLD", "BUY", "SELL", "EXIT"]
    reason: str
    stop_loss: float | None = None
    take_profit: float | None = None
    risk_fraction_pct: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Signal):
            return self.action == other.value
        return super().__eq__(other)

    @model_validator(mode="after")
    def validate_stop_fields(self) -> TradeIntent:
        if self.action in {"HOLD", "EXIT", "SELL"} and self.stop_loss is not None:
            return self
        if self.action == "BUY" and self.stop_loss is not None and self.stop_loss <= 0:
            raise ValueError("stop_loss must be positive")
        return self

    @classmethod
    def hold(cls, reason: str = "hold") -> TradeIntent:
        return cls(action="HOLD", reason=reason)

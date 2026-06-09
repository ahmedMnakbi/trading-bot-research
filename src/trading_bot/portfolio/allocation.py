from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AllocationPlan:
    symbol: str
    strategy: str
    quantity: float
    notional: float
    cash_after: float


def plan_allocation(
    *,
    symbol: str,
    strategy: str,
    quantity: float,
    price: float,
    cash: float,
    fee_bps: float,
) -> AllocationPlan:
    notional = quantity * price
    fee = notional * fee_bps / 10_000
    return AllocationPlan(
        symbol=symbol,
        strategy=strategy,
        quantity=quantity,
        notional=notional,
        cash_after=cash - notional - fee,
    )

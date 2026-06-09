from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSizeResult:
    quantity: float
    notional: float
    risk_amount: float
    risk_per_unit: float


def fixed_fractional_position_size(
    *,
    equity: float,
    cash: float,
    entry_price: float,
    stop_loss: float | None,
    risk_per_trade_pct: float,
    fee_bps: float,
    max_total_exposure_pct: float,
    min_stop_distance_bps: float,
    max_stop_distance_pct: float,
) -> PositionSizeResult:
    if stop_loss is None:
        raise ValueError("stop_loss is required")
    if stop_loss >= entry_price:
        raise ValueError("stop_loss must be below entry price for long trades")
    risk_per_unit = entry_price - stop_loss
    stop_distance_bps = risk_per_unit / entry_price * 10_000
    stop_distance_pct = risk_per_unit / entry_price * 100
    if stop_distance_bps < min_stop_distance_bps:
        raise ValueError("stop distance is too small")
    if stop_distance_pct > max_stop_distance_pct:
        raise ValueError("stop distance is too large")
    risk_amount = equity * risk_per_trade_pct / 100
    quantity = risk_amount / risk_per_unit
    max_notional_by_exposure = equity * max_total_exposure_pct / 100
    max_notional_by_cash = cash / (1 + fee_bps / 10_000)
    max_notional = min(max_notional_by_exposure, max_notional_by_cash)
    notional = quantity * entry_price
    if notional > max_notional:
        quantity = max_notional / entry_price
        notional = max_notional
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    return PositionSizeResult(
        quantity=quantity,
        notional=notional,
        risk_amount=risk_amount,
        risk_per_unit=risk_per_unit,
    )


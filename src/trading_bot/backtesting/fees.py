from __future__ import annotations


def calculate_fee(notional: float, fee_bps: float) -> float:
    if fee_bps < 0:
        raise ValueError("fee_bps must be non-negative")
    return notional * fee_bps / 10_000


from __future__ import annotations


def validate_long_stop(entry_price: float, stop_loss: float | None) -> None:
    if stop_loss is None:
        raise ValueError("stop_loss is required")
    if stop_loss <= 0 or stop_loss >= entry_price:
        raise ValueError("stop_loss must be below entry price")

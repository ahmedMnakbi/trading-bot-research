from __future__ import annotations

from datetime import UTC, datetime

from trading_bot.backtesting.events import OrderSide, OrderStatus
from trading_bot.execution.simulated import SimulatedExecutionClient
from trading_bot.execution.types import ExecutionOrderRequest


def request(**overrides):  # type: ignore[no-untyped-def]
    data = {
        "symbol": "BTC/USDT",
        "side": OrderSide.BUY,
        "quantity": 1,
        "requested_price": 100,
        "timestamp": datetime(2024, 1, 1, tzinfo=UTC),
    }
    data.update(overrides)
    return ExecutionOrderRequest(**data)


def test_simulated_execution_rejects_real_order_flag() -> None:
    result = SimulatedExecutionClient(fee_bps=0, slippage_bps=0).submit_order(
        request(real_order=True)
    )

    assert result.status == OrderStatus.REJECTED
    assert result.reason == "real_orders_forbidden"


def test_simulated_execution_rejects_private_api_config() -> None:
    try:
        SimulatedExecutionClient(fee_bps=0, slippage_bps=0, private_api_config={"apiKey": "x"})
    except ValueError as exc:
        assert "private" in str(exc)
    else:
        raise AssertionError("expected private API config rejection")


def test_simulated_execution_rejects_leverage() -> None:
    result = SimulatedExecutionClient(fee_bps=0, slippage_bps=0).submit_order(
        request(leverage=2)
    )

    assert result.reason == "leverage_rejected"


def test_simulated_execution_rejects_shorting() -> None:
    result = SimulatedExecutionClient(fee_bps=0, slippage_bps=0).submit_order(
        request(side=OrderSide.SELL, reason="short_entry")
    )

    assert result.reason == "shorting_rejected"


def test_simulated_execution_rejects_orders_when_kill_switch_is_active() -> None:
    client = SimulatedExecutionClient(fee_bps=0, slippage_bps=0)
    client.set_kill_switch(True)

    result = client.submit_order(request())

    assert result.reason == "kill_switch"


def test_simulated_execution_never_imports_ccxt() -> None:
    import sys

    assert "trading_bot.execution.simulated" in sys.modules
    assert "ccxt" not in SimulatedExecutionClient.__module__


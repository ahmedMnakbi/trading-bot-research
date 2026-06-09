from __future__ import annotations

from datetime import UTC, datetime

from trading_bot.backtesting.events import OrderRequest, OrderSide, OrderStatus
from trading_bot.backtesting.simulated_broker import SimulatedBroker


def test_fees_reduce_final_equity() -> None:
    broker = SimulatedBroker(
        starting_equity=1000,
        fee_bps=10,
        slippage_bps=0,
        reject_orders_without_stop=False,
    )
    timestamp = datetime(2024, 1, 1, tzinfo=UTC)

    broker.submit_order(
        OrderRequest("BTC/USDT", OrderSide.BUY, 1), timestamp=timestamp, next_open=100
    )
    broker.submit_order(
        OrderRequest("BTC/USDT", OrderSide.SELL, 1), timestamp=timestamp, next_open=100
    )

    assert broker.account_state().total_equity() < 1000
    assert broker.fees_paid > 0


def test_slippage_reduces_final_equity() -> None:
    broker = SimulatedBroker(
        starting_equity=1000,
        fee_bps=0,
        slippage_bps=50,
        reject_orders_without_stop=False,
    )
    timestamp = datetime(2024, 1, 1, tzinfo=UTC)

    broker.submit_order(
        OrderRequest("BTC/USDT", OrderSide.BUY, 1), timestamp=timestamp, next_open=100
    )
    broker.submit_order(
        OrderRequest("BTC/USDT", OrderSide.SELL, 1), timestamp=timestamp, next_open=100
    )

    assert broker.account_state().total_equity() < 1000
    assert broker.slippage_paid_estimate > 0


def test_broker_rejects_short_orders() -> None:
    broker = SimulatedBroker(
        starting_equity=1000,
        fee_bps=0,
        slippage_bps=0,
        allow_shorting=False,
        reject_orders_without_stop=False,
    )

    order = broker.submit_order(
        OrderRequest("BTC/USDT", OrderSide.SELL, 1),
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        next_open=100,
    )

    assert order.status == OrderStatus.REJECTED
    assert order.reason == "shorting_disabled"


def test_broker_rejects_leverage() -> None:
    broker = SimulatedBroker(
        starting_equity=1000,
        fee_bps=0,
        slippage_bps=0,
        allow_leverage=False,
        reject_orders_without_stop=False,
    )

    order = broker.submit_order(
        OrderRequest("BTC/USDT", OrderSide.BUY, 1, leverage=2),
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        next_open=100,
    )

    assert order.status == OrderStatus.REJECTED
    assert order.reason == "leverage_disabled"


def test_broker_rejects_orders_exceeding_cash() -> None:
    broker = SimulatedBroker(
        starting_equity=100,
        fee_bps=0,
        slippage_bps=0,
        reject_orders_without_stop=False,
    )

    order = broker.submit_order(
        OrderRequest("BTC/USDT", OrderSide.BUY, 2),
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        next_open=100,
    )

    assert order.status == OrderStatus.REJECTED
    assert order.reason == "insufficient_cash"


def test_broker_rejects_orders_when_kill_switch_is_active() -> None:
    broker = SimulatedBroker(
        starting_equity=1000,
        fee_bps=0,
        slippage_bps=0,
        reject_orders_without_stop=False,
    )
    broker.set_kill_switch(True)

    order = broker.submit_order(
        OrderRequest("BTC/USDT", OrderSide.BUY, 1),
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        next_open=100,
    )

    assert order.status == OrderStatus.REJECTED
    assert order.reason == "kill_switch_active"


def test_broker_rejects_stop_less_orders_when_stops_are_required() -> None:
    broker = SimulatedBroker(
        starting_equity=1000,
        fee_bps=0,
        slippage_bps=0,
        reject_orders_without_stop=True,
    )

    order = broker.submit_order(
        OrderRequest("BTC/USDT", OrderSide.BUY, 1),
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        next_open=100,
    )

    assert order.status == OrderStatus.REJECTED
    assert order.reason == "stop_loss_required"


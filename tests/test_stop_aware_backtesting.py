from __future__ import annotations

from datetime import UTC, datetime

from trading_bot.backtesting.events import OrderRequest, OrderSide
from trading_bot.backtesting.simulated_broker import SimulatedBroker


def broker_with_position(*, stop: float = 95, target: float | None = 110) -> SimulatedBroker:
    broker = SimulatedBroker(
        starting_equity=1000,
        fee_bps=0,
        slippage_bps=0,
        reject_orders_without_stop=True,
    )
    broker.submit_order(
        OrderRequest("BTC/USDT", OrderSide.BUY, 1, stop_loss=stop, take_profit=target),
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        next_open=100,
    )
    return broker


def test_broker_executes_stop_loss_when_candle_low_crosses_stop() -> None:
    broker = broker_with_position(stop=95)
    broker.process_protective_exit(
        timestamp=datetime(2024, 1, 2, tzinfo=UTC), candle_low=94, candle_high=105
    )

    assert broker.trades[-1].reason == "stop_loss"


def test_broker_executes_take_profit_when_candle_high_crosses_target() -> None:
    broker = broker_with_position(stop=95, target=110)
    broker.process_protective_exit(
        timestamp=datetime(2024, 1, 2, tzinfo=UTC), candle_low=96, candle_high=111
    )

    assert broker.trades[-1].reason == "take_profit"


def test_broker_assumes_stop_loss_first_if_both_stop_and_take_profit_are_hit() -> None:
    broker = broker_with_position(stop=95, target=110)
    broker.process_protective_exit(
        timestamp=datetime(2024, 1, 2, tzinfo=UTC), candle_low=94, candle_high=111
    )

    assert broker.trades[-1].reason == "stop_loss"

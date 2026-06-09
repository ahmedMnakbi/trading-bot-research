from __future__ import annotations

from datetime import datetime

from trading_bot.backtesting.events import (
    OrderRecord,
    OrderRequest,
    OrderSide,
    OrderStatus,
    TradeRecord,
)
from trading_bot.backtesting.fees import calculate_fee
from trading_bot.backtesting.slippage import apply_slippage
from trading_bot.portfolio.account import AccountState
from trading_bot.portfolio.position import Position


class SimulatedBroker:
    def __init__(
        self,
        *,
        starting_equity: float,
        fee_bps: float,
        slippage_bps: float,
        allow_shorting: bool = False,
        allow_leverage: bool = False,
        reject_orders_without_stop: bool = True,
        min_cash_pct: float = 0,
    ) -> None:
        if fee_bps < 0 or slippage_bps < 0:
            raise ValueError("fee_bps and slippage_bps must be non-negative")
        self.starting_equity = starting_equity
        self.cash = starting_equity
        self.realized_pnl = 0.0
        self.fees_paid = 0.0
        self.slippage_paid_estimate = 0.0
        self.position: Position | None = None
        self.allow_shorting = allow_shorting
        self.allow_leverage = allow_leverage
        self.reject_orders_without_stop = reject_orders_without_stop
        self.min_cash_pct = min_cash_pct
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps
        self.kill_switch_active = False
        self.orders: list[OrderRecord] = []
        self.trades: list[TradeRecord] = []
        self._entry_timestamp: datetime | None = None
        self._entry_fee = 0.0

    def account_state(self, mark_price: float | None = None) -> AccountState:
        equity = self.cash if self.position is None else self.cash + self.position.quantity * (
            mark_price if mark_price is not None else self.position.entry_price
        )
        unrealized = 0.0
        if self.position is not None and mark_price is not None:
            unrealized = self.position.quantity * (mark_price - self.position.entry_price)
        return AccountState(
            cash=self.cash,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=unrealized,
            position=self.position,
            fees_paid=self.fees_paid,
            slippage_paid_estimate=self.slippage_paid_estimate,
            equity=equity,
        )

    def set_kill_switch(self, active: bool) -> None:
        self.kill_switch_active = active

    def submit_order(
        self, order: OrderRequest, *, timestamp: datetime, next_open: float
    ) -> OrderRecord:
        rejection = self._rejection_reason(order)
        if rejection is not None:
            return self._record_rejection(order, timestamp, next_open, rejection)

        fill_price, slippage_per_unit = apply_slippage(next_open, order.side, self.slippage_bps)
        notional = order.quantity * fill_price
        fee = calculate_fee(notional, self.fee_bps)
        if order.side == OrderSide.BUY:
            total_cost = notional + fee
            min_cash = self.starting_equity * self.min_cash_pct / 100
            if total_cost > self.cash or self.cash - total_cost < min_cash:
                return self._record_rejection(order, timestamp, next_open, "insufficient_cash")
            self.cash -= total_cost
            self.position = Position(
                order.symbol,
                order.quantity,
                fill_price,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
            )
            self._entry_timestamp = timestamp
            self._entry_fee = fee
        else:
            if self.position is None or order.quantity > self.position.quantity:
                return self._record_rejection(order, timestamp, next_open, "no_long_position")
            proceeds = notional - fee
            entry = self.position
            pnl = (fill_price - entry.entry_price) * order.quantity - self._entry_fee - fee
            self.cash += proceeds
            self.realized_pnl += pnl
            self.trades.append(
                TradeRecord(
                    entry_timestamp=self._entry_timestamp or timestamp,
                    exit_timestamp=timestamp,
                    symbol=order.symbol,
                    quantity=order.quantity,
                    entry_price=entry.entry_price,
                    exit_price=fill_price,
                    pnl=pnl,
                    fees=self._entry_fee + fee,
                    reason=order.reason,
                )
            )
            self.position = None
            self._entry_timestamp = None
            self._entry_fee = 0.0

        self.fees_paid += fee
        self.slippage_paid_estimate += slippage_per_unit * order.quantity
        record = OrderRecord(
            timestamp=timestamp,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            requested_price=next_open,
            fill_price=fill_price,
            status=OrderStatus.FILLED,
            reason=None,
            fee=fee,
            slippage_paid_estimate=slippage_per_unit * order.quantity,
        )
        self.orders.append(record)
        return record

    def process_protective_exit(
        self,
        *,
        timestamp: datetime,
        candle_low: float,
        candle_high: float,
    ) -> OrderRecord | None:
        if self.position is None:
            return None
        if self.position.stop_loss is not None and candle_low <= self.position.stop_loss:
            return self.submit_order(
                OrderRequest(
                    symbol=self.position.symbol,
                    side=OrderSide.SELL,
                    quantity=self.position.quantity,
                    reason="stop_loss",
                ),
                timestamp=timestamp,
                next_open=self.position.stop_loss,
            )
        if self.position.take_profit is not None and candle_high >= self.position.take_profit:
            return self.submit_order(
                OrderRequest(
                    symbol=self.position.symbol,
                    side=OrderSide.SELL,
                    quantity=self.position.quantity,
                    reason="take_profit",
                ),
                timestamp=timestamp,
                next_open=self.position.take_profit,
            )
        return None

    def _rejection_reason(self, order: OrderRequest) -> str | None:
        if self.kill_switch_active:
            return "kill_switch_active"
        if order.quantity <= 0:
            return "invalid_quantity"
        if order.leverage != 1 and not self.allow_leverage:
            return "leverage_disabled"
        if order.side == OrderSide.SELL and self.position is None and not self.allow_shorting:
            return "shorting_disabled"
        if (
            self.reject_orders_without_stop
            and order.side == OrderSide.BUY
            and order.stop_loss is None
        ):
            return "stop_loss_required"
        return None

    def _record_rejection(
        self, order: OrderRequest, timestamp: datetime, requested_price: float, reason: str
    ) -> OrderRecord:
        record = OrderRecord(
            timestamp=timestamp,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            requested_price=requested_price,
            fill_price=None,
            status=OrderStatus.REJECTED,
            reason=reason,
        )
        self.orders.append(record)
        return record

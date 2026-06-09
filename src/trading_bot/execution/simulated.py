from __future__ import annotations

from trading_bot.backtesting.events import OrderSide, OrderStatus
from trading_bot.backtesting.fees import calculate_fee
from trading_bot.backtesting.slippage import apply_slippage
from trading_bot.execution.types import ExecutionOrderRequest, OrderResult


class SimulatedExecutionClient:
    def __init__(
        self,
        *,
        fee_bps: float,
        slippage_bps: float,
        simulated_latency_ms: int = 0,
        private_api_config: dict[str, object] | None = None,
    ) -> None:
        if private_api_config:
            raise ValueError("private API config is prohibited for simulated execution")
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps
        self.simulated_latency_ms = simulated_latency_ms
        self.kill_switch_active = False

    def set_kill_switch(self, active: bool) -> None:
        self.kill_switch_active = active

    def submit_order(self, order_request: ExecutionOrderRequest) -> OrderResult:
        if order_request.real_order:
            return self._rejected(order_request, "real_orders_forbidden")
        if self.kill_switch_active:
            return self._rejected(order_request, "kill_switch")
        if order_request.leverage != 1:
            return self._rejected(order_request, "leverage_rejected")
        if order_request.side == OrderSide.SELL and order_request.reason == "short_entry":
            return self._rejected(order_request, "shorting_rejected")
        fill_price, slippage_per_unit = apply_slippage(
            order_request.requested_price,
            order_request.side,
            self.slippage_bps,
        )
        notional = fill_price * order_request.quantity
        fee = calculate_fee(notional, self.fee_bps)
        return OrderResult(
            symbol=order_request.symbol,
            side=order_request.side,
            quantity=order_request.quantity,
            requested_price=order_request.requested_price,
            fill_price=fill_price,
            status=OrderStatus.FILLED,
            reason=order_request.reason,
            fee=fee,
            slippage_paid_estimate=slippage_per_unit * order_request.quantity,
            metadata={"simulated_latency_ms": self.simulated_latency_ms, "real_order": False},
        )

    def _rejected(self, order_request: ExecutionOrderRequest, reason: str) -> OrderResult:
        return OrderResult(
            symbol=order_request.symbol,
            side=order_request.side,
            quantity=order_request.quantity,
            requested_price=order_request.requested_price,
            fill_price=None,
            status=OrderStatus.REJECTED,
            reason=reason,
            metadata={"simulated_latency_ms": self.simulated_latency_ms, "real_order": False},
        )

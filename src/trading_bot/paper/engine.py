from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from trading_bot.backtesting.events import OrderSide, OrderStatus
from trading_bot.data.latest import fetch_latest_public_ohlcv
from trading_bot.data.models import OhlcvCandle
from trading_bot.data.provider import MarketDataProvider
from trading_bot.execution.simulated import SimulatedExecutionClient
from trading_bot.execution.types import ExecutionOrderRequest
from trading_bot.monitoring.alerts import emit_alert
from trading_bot.monitoring.health import health_event
from trading_bot.paper.decision_log import PaperDecisionLogger
from trading_bot.paper.scheduler import iteration_schedule
from trading_bot.paper.state import PaperPosition, PaperState, new_paper_state
from trading_bot.paper.store import PaperStateStore, append_jsonl
from trading_bot.portfolio.account import AccountState
from trading_bot.portfolio.position import Position
from trading_bot.risk.position_sizing import fixed_fractional_position_size
from trading_bot.strategies.base import Strategy


class PaperTradingError(RuntimeError):
    """Raised when paper trading cannot run safely."""


class PaperTradingEngine:
    def __init__(
        self,
        *,
        provider: MarketDataProvider,
        execution: SimulatedExecutionClient,
        store: PaperStateStore,
        decision_logger: PaperDecisionLogger,
        strategy: Strategy,
        exchange: str,
        symbol: str,
        timeframe: str,
        starting_equity: float,
        fee_bps: float,
        risk_per_trade_pct: float,
        max_total_exposure_pct: float,
        min_stop_distance_bps: float,
        max_stop_distance_pct: float,
        max_consecutive_data_errors: int,
        allow_partial_latest_candle: bool,
        resume_existing_state: bool,
        persist_state: bool,
        validation_run_id: str | None,
    ) -> None:
        self.provider = provider
        self.execution = execution
        self.store = store
        self.decision_logger = decision_logger
        self.strategy = strategy
        self.exchange = exchange
        self.symbol = symbol
        self.timeframe = timeframe
        self.starting_equity = starting_equity
        self.fee_bps = fee_bps
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_total_exposure_pct = max_total_exposure_pct
        self.min_stop_distance_bps = min_stop_distance_bps
        self.max_stop_distance_pct = max_stop_distance_pct
        self.max_consecutive_data_errors = max_consecutive_data_errors
        self.allow_partial_latest_candle = allow_partial_latest_candle
        self.resume_existing_state = resume_existing_state
        self.persist_state = persist_state
        self.validation_run_id = validation_run_id

    def run(self, *, max_iterations: int | None = None) -> PaperState:
        state = self._load_or_create_state()
        for _iteration in iteration_schedule(max_iterations):
            try:
                candles = fetch_latest_public_ohlcv(
                    provider=self.provider,
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    limit=500,
                    allow_partial_latest_candle=self.allow_partial_latest_candle,
                )
            except Exception as exc:
                state = self._record_data_error(state, f"public data fetch failed: {exc}")
                continue
            if not candles:
                state = self._record_data_error(
                    state, "empty public data response", code="DATA_EMPTY"
                )
                continue
            new_candles = [
                candle
                for candle in candles
                if state.last_processed_candle_timestamp is None
                or candle.timestamp > state.last_processed_candle_timestamp
            ]
            if not new_candles:
                self._write_health(state, "DUPLICATE_CANDLE", "no new candle to process")
                continue
            state.consecutive_data_errors = 0
            for candle in new_candles:
                state = self._process_candle(state, candles, candle)
        if self.persist_state:
            self._save_state(state)
        return state

    def _load_or_create_state(self) -> PaperState:
        if self.resume_existing_state:
            existing = self.store.latest_state(
                exchange=self.exchange,
                symbol=self.symbol,
                timeframe=self.timeframe,
                strategy=self.strategy.name,
            )
            if existing is not None:
                return existing
        state = new_paper_state(
            exchange=self.exchange,
            symbol=self.symbol,
            timeframe=self.timeframe,
            strategy=self.strategy.name,
            starting_equity=self.starting_equity,
        )
        self._save_state(state)
        return state

    def _process_candle(
        self, state: PaperState, candles: list[OhlcvCandle], candle: OhlcvCandle
    ) -> PaperState:
        before_position = state.open_position.model_dump() if state.open_position else None
        equity_before = state.equity
        account = self._account_state(state, mark_price=candle.close)
        visible = _candles_to_frame(
            [item for item in candles if item.timestamp <= candle.timestamp]
        )
        try:
            intent = self.strategy.generate_signal(visible, len(visible) - 1, account)
        except Exception as exc:
            self._write_health(state, "STRATEGY_ERROR", str(exc))
            intent = None
        risk_decision = "accepted"
        order_decision = "no_order"
        warnings: list[str] = []
        if intent is not None and intent.action == "BUY" and state.open_position is None:
            try:
                sizing = fixed_fractional_position_size(
                    equity=state.equity,
                    cash=state.cash,
                    entry_price=candle.close,
                    stop_loss=intent.stop_loss,
                    risk_per_trade_pct=intent.risk_fraction_pct or self.risk_per_trade_pct,
                    fee_bps=self.fee_bps,
                    max_total_exposure_pct=self.max_total_exposure_pct,
                    min_stop_distance_bps=self.min_stop_distance_bps,
                    max_stop_distance_pct=self.max_stop_distance_pct,
                )
            except ValueError:
                risk_decision = "risk_rejected"
                order_decision = "none"
                warnings.append("RISK_REJECTED")
                self._write_health(state, "RISK_REJECTED", "paper trade intent rejected by risk")
            else:
                result = self.execution.submit_order(
                    ExecutionOrderRequest(
                        symbol=self.symbol,
                        side=OrderSide.BUY,
                        quantity=sizing.quantity,
                        requested_price=candle.close,
                        timestamp=candle.timestamp,
                        stop_loss=intent.stop_loss,
                        take_profit=intent.take_profit,
                        reason=intent.reason,
                    )
                )
                state.orders.append(_result_to_order_dict(result, candle.timestamp))
                if result.status == OrderStatus.FILLED and result.fill_price is not None:
                    state.cash -= result.fill_price * result.quantity + result.fee
                    state.open_position = PaperPosition(
                        symbol=self.symbol,
                        quantity=result.quantity,
                        entry_price=result.fill_price,
                        stop_loss=intent.stop_loss,
                        take_profit=intent.take_profit,
                    )
                    state.fees_paid += result.fee
                    state.slippage_paid_estimate += result.slippage_paid_estimate
                    order_decision = "simulated_order_created"
                else:
                    state.consecutive_order_errors += 1
                    order_decision = "simulated_order_rejected"
                    self._write_health(state, "ORDER_REJECTED", result.reason or "order rejected")
        elif intent is not None and intent.action in {"SELL", "EXIT"} and state.open_position:
            result = self.execution.submit_order(
                ExecutionOrderRequest(
                    symbol=self.symbol,
                    side=OrderSide.SELL,
                    quantity=state.open_position.quantity,
                    requested_price=candle.close,
                    timestamp=candle.timestamp,
                    reason=intent.reason,
                )
            )
            state.orders.append(_result_to_order_dict(result, candle.timestamp))
            if result.status == OrderStatus.FILLED and result.fill_price is not None:
                entry = state.open_position
                proceeds = result.fill_price * result.quantity - result.fee
                pnl = (result.fill_price - entry.entry_price) * result.quantity - result.fee
                state.cash += proceeds
                state.realized_pnl += pnl
                state.fees_paid += result.fee
                state.slippage_paid_estimate += result.slippage_paid_estimate
                state.trades.append(
                    {
                        "entry_price": entry.entry_price,
                        "exit_price": result.fill_price,
                        "quantity": result.quantity,
                        "pnl": pnl,
                        "fees": result.fee,
                        "reason": intent.reason,
                        "exit_timestamp": candle.timestamp,
                    }
                )
                state.open_position = None
                order_decision = "simulated_order_created"
            else:
                state.consecutive_order_errors += 1
                order_decision = "simulated_order_rejected"
                self._write_health(state, "ORDER_REJECTED", result.reason or "order rejected")
        state.last_processed_candle_timestamp = candle.timestamp
        state.updated_at = datetime.now(UTC)
        state.unrealized_pnl = _unrealized(state, candle.close)
        state.equity = state.cash + _position_value(state, candle.close)
        state.equity_curve.append({"timestamp": candle.timestamp, "equity": state.equity})
        decision = {
            "timestamp": datetime.now(UTC),
            "paper_run_id": state.paper_run_id,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "strategy": self.strategy.name,
            "candle_timestamp": candle.timestamp,
            "intent_action": intent.action if intent else "HOLD",
            "intent_reason": intent.reason if intent else "strategy_error",
            "stop_loss": intent.stop_loss if intent else None,
            "take_profit": intent.take_profit if intent else None,
            "risk_fraction_pct": intent.risk_fraction_pct if intent else None,
            "risk_decision": risk_decision,
            "order_decision": order_decision,
            "position_before": before_position,
            "position_after": state.open_position.model_dump() if state.open_position else None,
            "equity_before": equity_before,
            "equity_after": state.equity,
            "warnings": warnings,
            "live_trading": False,
            "real_order": False,
        }
        self.decision_logger.write(state.paper_run_id, decision)
        if self.persist_state:
            self._save_state(state)
        return state

    def _record_data_error(
        self, state: PaperState, message: str, *, code: str = "DATA_STALE"
    ) -> PaperState:
        state.consecutive_data_errors += 1
        self._write_health(state, code, message)
        if state.consecutive_data_errors >= self.max_consecutive_data_errors:
            state.kill_switch_active = True
            self.execution.set_kill_switch(True)
            self._write_health(state, "KILL_SWITCH_ACTIVE", "too many consecutive data errors")
        state.updated_at = datetime.now(UTC)
        if self.persist_state:
            self._save_state(state)
        return state

    def _account_state(self, state: PaperState, *, mark_price: float) -> AccountState:
        position = None
        if state.open_position:
            position = Position(
                state.open_position.symbol,
                state.open_position.quantity,
                state.open_position.entry_price,
                state.open_position.stop_loss,
                state.open_position.take_profit,
            )
        return AccountState(
            cash=state.cash,
            realized_pnl=state.realized_pnl,
            unrealized_pnl=_unrealized(state, mark_price),
            position=position,
            fees_paid=state.fees_paid,
            slippage_paid_estimate=state.slippage_paid_estimate,
            equity=state.cash + _position_value(state, mark_price),
        )

    def _save_state(self, state: PaperState) -> None:
        metadata = {
            "paper_run_id": state.paper_run_id,
            "created_at": state.created_at,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "strategy": self.strategy.name,
            "starting_equity": self.starting_equity,
            "live_trading": False,
            "real_orders_enabled": False,
            "uses_private_api": False,
            "validation_run_id": self.validation_run_id,
        }
        try:
            self.store.save(state, metadata)
            run_dir = self.store.run_dir(state.paper_run_id)
            (run_dir / "health_events.jsonl").touch(exist_ok=True)
            (run_dir / "alerts.jsonl").touch(exist_ok=True)
        except Exception:
            run_dir = self.store.run_dir(state.paper_run_id)
            append_jsonl(
                run_dir / "health_events.jsonl",
                health_event("STATE_WRITE_FAILED", "state write failed"),
            )
            raise

    def _write_health(self, state: PaperState, code: str, message: str) -> None:
        run_dir = self.store.run_dir(state.paper_run_id)
        event = health_event(code, message)
        append_jsonl(run_dir / "health_events.jsonl", event)
        alert_codes = {
            "KILL_SWITCH_ACTIVE",
            "ORDER_REJECTED",
            "RISK_REJECTED",
            "DATA_EMPTY",
            "DATA_STALE",
        }
        if code in alert_codes:
            emit_alert(run_dir=run_dir, event=event, console=False)


def _unrealized(state: PaperState, price: float) -> float:
    if state.open_position is None:
        return 0.0
    return state.open_position.quantity * (price - state.open_position.entry_price)


def _position_value(state: PaperState, price: float) -> float:
    if state.open_position is None:
        return 0.0
    return state.open_position.quantity * price


def _result_to_order_dict(result: Any, timestamp: datetime) -> dict[str, Any]:
    return {
        "timestamp": timestamp,
        "symbol": result.symbol,
        "side": result.side.value,
        "quantity": result.quantity,
        "requested_price": result.requested_price,
        "fill_price": result.fill_price,
        "status": result.status.value,
        "reason": result.reason,
        "fee": result.fee,
        "slippage_paid_estimate": result.slippage_paid_estimate,
    }


def _candles_to_frame(candles: list[OhlcvCandle]):
    import pandas as pd

    return pd.DataFrame(
        [
            {
                "timestamp": candle.timestamp,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            }
            for candle in candles
        ]
    )

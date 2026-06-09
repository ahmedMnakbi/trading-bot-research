from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from trading_bot.backtesting.events import OrderSide, OrderStatus
from trading_bot.data.latest import fetch_latest_public_ohlcv
from trading_bot.data.models import OhlcvCandle
from trading_bot.data.provider import MarketDataProvider
from trading_bot.data.validation import validate_candles
from trading_bot.execution.simulated import SimulatedExecutionClient
from trading_bot.execution.types import ExecutionOrderRequest
from trading_bot.monitoring.alerts import emit_alert
from trading_bot.monitoring.health import health_event
from trading_bot.paper.scheduler import iteration_schedule
from trading_bot.paper.store import PortfolioPaperStateStore, append_jsonl
from trading_bot.portfolio.account import AccountState
from trading_bot.portfolio.allocation import plan_allocation
from trading_bot.portfolio.exposure import calculate_exposure_snapshot
from trading_bot.portfolio.portfolio_state import (
    PortfolioPaperState,
    PortfolioPosition,
    new_portfolio_paper_state,
)
from trading_bot.risk.portfolio_limits import evaluate_portfolio_entry
from trading_bot.risk.position_sizing import fixed_fractional_position_size
from trading_bot.strategies.base import Strategy


class PortfolioPaperTradingError(RuntimeError):
    """Raised when portfolio paper trading cannot run safely."""


class PortfolioPaperTradingEngine:
    def __init__(
        self,
        *,
        provider: MarketDataProvider,
        execution: SimulatedExecutionClient,
        store: PortfolioPaperStateStore,
        strategies: dict[str, Strategy],
        portfolio_risk: Any,
        exchange: str,
        symbols: list[str],
        timeframe: str,
        starting_equity: float,
        fee_bps: float,
        risk_per_trade_pct: float,
        min_stop_distance_bps: float,
        max_stop_distance_pct: float,
        max_consecutive_data_errors: int,
        allow_partial_latest_candle: bool,
        resume_existing_state: bool,
        persist_state: bool,
        campaign_run_id: str | None,
    ) -> None:
        self.provider = provider
        self.execution = execution
        self.store = store
        self.strategies = strategies
        self.portfolio_risk = portfolio_risk
        self.exchange = exchange
        self.symbols = symbols
        self.timeframe = timeframe
        self.starting_equity = starting_equity
        self.fee_bps = fee_bps
        self.risk_per_trade_pct = risk_per_trade_pct
        self.min_stop_distance_bps = min_stop_distance_bps
        self.max_stop_distance_pct = max_stop_distance_pct
        self.max_consecutive_data_errors = max_consecutive_data_errors
        self.allow_partial_latest_candle = allow_partial_latest_candle
        self.resume_existing_state = resume_existing_state
        self.persist_state = persist_state
        self.campaign_run_id = campaign_run_id

    def run(self, *, max_iterations: int | None = None) -> PortfolioPaperState:
        state = self._load_or_create_state()
        for _iteration in iteration_schedule(max_iterations):
            if state.kill_switch_active:
                self._write_health(state, "KILL_SWITCH_ACTIVE", "portfolio kill switch active")
                break
            new_positions = 0
            latest_prices: dict[str, float] = {}
            for symbol in self.symbols:
                candles = self._fetch_symbol_candles(state, symbol)
                if not candles:
                    continue
                latest_prices[symbol] = candles[-1].close
                new_candles = [
                    candle
                    for candle in candles
                    if state.last_processed_candle_by_symbol.get(symbol) is None
                    or candle.timestamp > state.last_processed_candle_by_symbol.get(symbol)
                ]
                if not new_candles:
                    self._write_health(state, "DUPLICATE_CANDLE", f"no new candle for {symbol}")
                    continue
                for candle in new_candles[-1:]:
                    state, opened = self._process_symbol_candle(
                        state, symbol, candles, candle, new_positions, latest_prices
                    )
                    if opened:
                        new_positions += 1
            self._mark_to_market(state, latest_prices)
            self._append_exposure(state, latest_prices)
            if self.persist_state:
                self._save_state(state)
        return state

    def _load_or_create_state(self) -> PortfolioPaperState:
        strategy_map = {symbol: self.strategies[symbol].name for symbol in self.symbols}
        if self.resume_existing_state:
            existing = self.store.latest_state(
                exchange=self.exchange,
                symbols=self.symbols,
                timeframe=self.timeframe,
                strategy_map=strategy_map,
            )
            if existing is not None:
                return existing
        state = new_portfolio_paper_state(
            exchange=self.exchange,
            timeframe=self.timeframe,
            symbols=self.symbols,
            strategy_map=strategy_map,
            starting_equity=self.starting_equity,
        )
        self._save_state(state)
        return state

    def _fetch_symbol_candles(
        self, state: PortfolioPaperState, symbol: str
    ) -> list[OhlcvCandle]:
        try:
            candles = fetch_latest_public_ohlcv(
                provider=self.provider,
                symbol=symbol,
                timeframe=self.timeframe,
                limit=500,
                allow_partial_latest_candle=self.allow_partial_latest_candle,
            )
            validate_candles(candles, self.timeframe, validate_continuity=False)
        except Exception as exc:
            state.consecutive_data_errors_by_symbol[symbol] = (
                state.consecutive_data_errors_by_symbol.get(symbol, 0) + 1
            )
            self._write_health(state, "DATA_ERROR", f"{symbol}: {exc}")
            if (
                state.consecutive_data_errors_by_symbol[symbol]
                >= self.max_consecutive_data_errors
            ):
                state.kill_switch_active = True
                self.execution.set_kill_switch(True)
                self._write_health(
                    state, "KILL_SWITCH_ACTIVE", f"too many data errors for {symbol}"
                )
            return []
        if not candles:
            self._write_health(state, "DATA_EMPTY", f"empty data for {symbol}")
            return []
        state.consecutive_data_errors_by_symbol[symbol] = 0
        return candles

    def _process_symbol_candle(
        self,
        state: PortfolioPaperState,
        symbol: str,
        candles: list[OhlcvCandle],
        candle: OhlcvCandle,
        new_positions_this_iteration: int,
        latest_prices: dict[str, float],
    ) -> tuple[PortfolioPaperState, bool]:
        strategy = self.strategies[symbol]
        visible = _candles_to_frame(
            [item for item in candles if item.timestamp <= candle.timestamp]
        )
        cash_before = state.cash
        equity_before = state.equity
        open_before = len(state.positions_by_symbol)
        warnings: list[str] = []
        order_decision = "no_order"
        risk_decision = "accepted"
        portfolio_risk_decision = "accepted"
        opened = False
        try:
            intent = strategy.generate_signal(
                visible,
                len(visible) - 1,
                self._account_state(state, symbol, candle.close),
            )
        except Exception as exc:
            intent = None
            warnings.append("STRATEGY_ERROR")
            self._write_health(state, "STRATEGY_ERROR", f"{symbol}: {exc}")

        if intent is not None and intent.action == "BUY":
            try:
                sizing = fixed_fractional_position_size(
                    equity=state.equity,
                    cash=state.cash,
                    entry_price=candle.close,
                    stop_loss=intent.stop_loss,
                    risk_per_trade_pct=intent.risk_fraction_pct or self.risk_per_trade_pct,
                    fee_bps=self.fee_bps,
                    max_total_exposure_pct=self.portfolio_risk.max_symbol_exposure_pct,
                    min_stop_distance_bps=self.min_stop_distance_bps,
                    max_stop_distance_pct=self.max_stop_distance_pct,
                )
                allocation = plan_allocation(
                    symbol=symbol,
                    strategy=strategy.name,
                    quantity=sizing.quantity,
                    price=candle.close,
                    cash=state.cash,
                    fee_bps=self.fee_bps,
                )
            except ValueError:
                risk_decision = "risk_rejected"
                portfolio_risk_decision = "risk_rejected"
                warnings.append("RISK_REJECTED")
                self._write_health(state, "RISK_REJECTED", f"{symbol}: invalid risk sizing")
            else:
                decision = evaluate_portfolio_entry(
                    state=state,
                    settings=self.portfolio_risk,
                    symbol=symbol,
                    strategy=strategy.name,
                    notional=allocation.notional,
                    cash_after=allocation.cash_after,
                    stop_loss=intent.stop_loss,
                    new_positions_this_iteration=new_positions_this_iteration,
                    correlation=_candidate_correlation(state, symbol),
                )
                warnings.extend(decision.warnings)
                if not decision.accepted:
                    portfolio_risk_decision = decision.reason
                    order_decision = "none"
                    self._write_health(
                        state, "PORTFOLIO_RISK_REJECTED", f"{symbol}: {decision.reason}"
                    )
                    if decision.kill_switch:
                        state.kill_switch_active = True
                        self.execution.set_kill_switch(True)
                else:
                    result = self.execution.submit_order(
                        ExecutionOrderRequest(
                            symbol=symbol,
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
                        state.positions_by_symbol[symbol] = PortfolioPosition(
                            symbol=symbol,
                            strategy=strategy.name,
                            quantity=result.quantity,
                            entry_price=result.fill_price,
                            stop_loss=intent.stop_loss,
                            take_profit=intent.take_profit,
                        )
                        state.fees_paid += result.fee
                        state.slippage_paid_estimate += result.slippage_paid_estimate
                        order_decision = "simulated_order_created"
                        opened = True
                    else:
                        state.consecutive_order_errors += 1
                        order_decision = "simulated_order_rejected"
                        self._write_health(
                            state, "ORDER_REJECTED", result.reason or "order rejected"
                        )
        elif intent is not None and intent.action in {"SELL", "EXIT"}:
            opened = False
            order_decision = self._close_position_if_present(state, symbol, candle, intent.reason)

        latest_prices[symbol] = candle.close
        self._mark_to_market(state, latest_prices)
        state.last_processed_candle_by_symbol[symbol] = candle.timestamp
        state.updated_at = datetime.now(UTC)
        snapshot = calculate_exposure_snapshot(
            state, timestamp=candle.timestamp, mark_prices=latest_prices
        )
        decision_record = {
            "timestamp": datetime.now(UTC),
            "portfolio_paper_run_id": state.portfolio_paper_run_id,
            "exchange": self.exchange,
            "symbol": symbol,
            "timeframe": self.timeframe,
            "strategy": strategy.name,
            "candle_timestamp": candle.timestamp,
            "intent_action": intent.action if intent else "HOLD",
            "intent_reason": intent.reason if intent else "strategy_error",
            "stop_loss": intent.stop_loss if intent else None,
            "take_profit": intent.take_profit if intent else None,
            "risk_decision": risk_decision,
            "portfolio_risk_decision": portfolio_risk_decision,
            "order_decision": order_decision,
            "cash_before": cash_before,
            "cash_after": state.cash,
            "equity_before": equity_before,
            "equity_after": state.equity,
            "open_positions_before": open_before,
            "open_positions_after": len(state.positions_by_symbol),
            "symbol_exposure_pct_after": snapshot["symbol_exposure_pct"].get(symbol, 0),
            "portfolio_exposure_pct_after": snapshot["gross_exposure_pct"],
            "warnings": warnings,
            "live_trading": False,
            "real_order": False,
        }
        append_jsonl(
            self.store.run_dir(state.portfolio_paper_run_id) / "decisions.jsonl",
            decision_record,
        )
        if self.persist_state:
            self._save_state(state)
        return state, opened

    def _close_position_if_present(
        self, state: PortfolioPaperState, symbol: str, candle: OhlcvCandle, reason: str
    ) -> str:
        position = state.positions_by_symbol.get(symbol)
        if position is None:
            return "no_order"
        result = self.execution.submit_order(
            ExecutionOrderRequest(
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=position.quantity,
                requested_price=candle.close,
                timestamp=candle.timestamp,
                reason=reason,
            )
        )
        state.orders.append(_result_to_order_dict(result, candle.timestamp))
        if result.status == OrderStatus.FILLED and result.fill_price is not None:
            proceeds = result.fill_price * result.quantity - result.fee
            pnl = (result.fill_price - position.entry_price) * result.quantity - result.fee
            state.cash += proceeds
            state.realized_pnl += pnl
            state.fees_paid += result.fee
            state.slippage_paid_estimate += result.slippage_paid_estimate
            state.trades.append(
                {
                    "symbol": symbol,
                    "strategy": position.strategy,
                    "entry_price": position.entry_price,
                    "exit_price": result.fill_price,
                    "quantity": result.quantity,
                    "pnl": pnl,
                    "fees": result.fee,
                    "reason": reason,
                    "exit_timestamp": candle.timestamp,
                }
            )
            del state.positions_by_symbol[symbol]
            return "simulated_order_created"
        state.consecutive_order_errors += 1
        return "simulated_order_rejected"

    def _account_state(
        self, state: PortfolioPaperState, symbol: str, mark_price: float
    ) -> AccountState:
        position = None
        if symbol in state.positions_by_symbol:
            existing = state.positions_by_symbol[symbol]
            from trading_bot.portfolio.position import Position

            position = Position(
                existing.symbol,
                existing.quantity,
                existing.entry_price,
                existing.stop_loss,
                existing.take_profit,
            )
        return AccountState(
            cash=state.cash,
            realized_pnl=state.realized_pnl,
            unrealized_pnl=state.unrealized_pnl,
            position=position,
            fees_paid=state.fees_paid,
            slippage_paid_estimate=state.slippage_paid_estimate,
            equity=state.cash + _position_value(state, {symbol: mark_price}),
        )

    def _mark_to_market(self, state: PortfolioPaperState, prices: dict[str, float]) -> None:
        unrealized = 0.0
        value = 0.0
        for symbol, position in state.positions_by_symbol.items():
            price = prices.get(symbol, position.entry_price)
            value += position.market_value(price)
            unrealized += position.quantity * (price - position.entry_price)
        state.unrealized_pnl = unrealized
        state.equity = state.cash + value
        state.equity_curve.append({"timestamp": datetime.now(UTC), "equity": state.equity})

    def _append_exposure(self, state: PortfolioPaperState, prices: dict[str, float]) -> None:
        state.exposure_snapshots.append(
            calculate_exposure_snapshot(state, timestamp=datetime.now(UTC), mark_prices=prices)
        )

    def _save_state(self, state: PortfolioPaperState) -> None:
        metadata = {
            "portfolio_paper_run_id": state.portfolio_paper_run_id,
            "created_at": state.created_at,
            "exchange": self.exchange,
            "symbols": self.symbols,
            "timeframe": self.timeframe,
            "strategy_map": state.strategy_map,
            "starting_equity": self.starting_equity,
            "live_trading": False,
            "real_orders_enabled": False,
            "uses_private_api": False,
            "campaign_run_id": self.campaign_run_id,
        }
        self.store.save(state, metadata)
        run_dir = self.store.run_dir(state.portfolio_paper_run_id)
        (run_dir / "health_events.jsonl").touch(exist_ok=True)
        (run_dir / "alerts.jsonl").touch(exist_ok=True)

    def _write_health(self, state: PortfolioPaperState, code: str, message: str) -> None:
        run_dir = self.store.run_dir(state.portfolio_paper_run_id)
        event = health_event(code, message)
        append_jsonl(run_dir / "health_events.jsonl", event)
        if code in {
            "KILL_SWITCH_ACTIVE",
            "ORDER_REJECTED",
            "RISK_REJECTED",
            "DATA_EMPTY",
            "DATA_ERROR",
        }:
            emit_alert(run_dir=run_dir, event=event, console=False)


def _candidate_correlation(state: PortfolioPaperState, symbol: str) -> float | None:
    if symbol in state.positions_by_symbol or not state.positions_by_symbol:
        return None
    return 1.0


def _position_value(state: PortfolioPaperState, prices: dict[str, float]) -> float:
    return sum(
        position.market_value(prices.get(symbol))
        for symbol, position in state.positions_by_symbol.items()
    )


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
        "real_order": False,
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

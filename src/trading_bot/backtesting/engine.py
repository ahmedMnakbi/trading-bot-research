from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from trading_bot.backtesting.events import OrderRequest, OrderSide
from trading_bot.backtesting.metrics import calculate_metrics
from trading_bot.backtesting.results import BacktestResult, new_run_id, write_backtest_artifacts
from trading_bot.backtesting.simulated_broker import SimulatedBroker
from trading_bot.data.cache import OhlcvCache, candles_to_dataframe
from trading_bot.data.validation import validate_candles
from trading_bot.risk.position_sizing import fixed_fractional_position_size
from trading_bot.strategies.base import Strategy


class BacktestError(RuntimeError):
    """Raised when deterministic local backtesting cannot run."""


def run_backtest_from_cache(
    *,
    cache_dir: str | Path,
    output_root: str | Path,
    exchange: str,
    symbol: str,
    timeframe: str,
    strategy: Strategy,
    starting_equity: float,
    fee_bps: float,
    slippage_bps: float,
    allow_shorting: bool,
    allow_leverage: bool,
    reject_orders_without_stop: bool,
    min_cash_pct: float,
    mark_to_market: bool,
    config_snapshot: dict[str, Any],
    risk_per_trade_pct: float = 0.25,
    max_total_exposure_pct: float = 30,
    min_stop_distance_bps: float = 10,
    max_stop_distance_pct: float = 100,
    max_bars: int | None = None,
    run_id: str | None = None,
) -> BacktestResult:
    cache = OhlcvCache(cache_dir)
    path = cache.path_for(exchange, symbol, timeframe)
    if not path.exists():
        raise BacktestError(f"missing cache file: {path}")
    candles = cache.read(exchange, symbol, timeframe)
    if not candles:
        raise BacktestError("empty OHLCV dataset")
    candles = candles[:max_bars] if max_bars else candles
    validate_candles(candles, timeframe, validate_continuity=True)
    if len(candles) < 2:
        raise BacktestError("at least two candles are required for next-open fills")
    return run_backtest_on_candles(
        candles=candles,
        output_root=output_root,
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        strategy=strategy,
        starting_equity=starting_equity,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        allow_shorting=allow_shorting,
        allow_leverage=allow_leverage,
        reject_orders_without_stop=reject_orders_without_stop,
        min_cash_pct=min_cash_pct,
        mark_to_market=mark_to_market,
        config_snapshot=config_snapshot,
        risk_per_trade_pct=risk_per_trade_pct,
        max_total_exposure_pct=max_total_exposure_pct,
        min_stop_distance_bps=min_stop_distance_bps,
        max_stop_distance_pct=max_stop_distance_pct,
        run_id=run_id,
        write_artifacts=True,
    )


def run_backtest_on_candles(
    *,
    candles: list[Any],
    output_root: str | Path,
    exchange: str,
    symbol: str,
    timeframe: str,
    strategy: Strategy,
    starting_equity: float,
    fee_bps: float,
    slippage_bps: float,
    allow_shorting: bool,
    allow_leverage: bool,
    reject_orders_without_stop: bool,
    min_cash_pct: float,
    mark_to_market: bool,
    config_snapshot: dict[str, Any],
    risk_per_trade_pct: float = 0.25,
    max_total_exposure_pct: float = 30,
    min_stop_distance_bps: float = 10,
    max_stop_distance_pct: float = 100,
    trade_start_index: int = 0,
    run_id: str | None = None,
    write_artifacts: bool = False,
) -> BacktestResult:
    if len(candles) < 2:
        raise BacktestError("at least two candles are required for next-open fills")
    if trade_start_index < 0 or trade_start_index >= len(candles):
        raise BacktestError("trade_start_index must point to an available candle")
    candles_df = candles_to_dataframe(candles)
    broker = SimulatedBroker(
        starting_equity=starting_equity,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        allow_shorting=allow_shorting,
        allow_leverage=allow_leverage,
        reject_orders_without_stop=reject_orders_without_stop,
        min_cash_pct=min_cash_pct,
    )
    equity_rows: list[dict[str, Any]] = []

    signal_start_index = max(trade_start_index - 1, 0)
    for index in range(len(candles_df) - 1):
        next_index = index + 1
        if next_index < trade_start_index:
            continue
        next_row = candles_df.iloc[index + 1]
        next_open = float(next_row["open"])
        timestamp = next_row["timestamp"]

        protective_exit = broker.process_protective_exit(
            timestamp=timestamp,
            candle_low=float(next_row["low"]),
            candle_high=float(next_row["high"]),
        )
        if protective_exit is None:
            visible = candles_df.iloc[: index + 1].copy()
            account = broker.account_state(mark_price=float(visible["close"].iloc[-1]))
            local_index = index - signal_start_index
            intent = strategy.generate_signal(visible, local_index, account)
            if intent.action == "BUY" and broker.position is None:
                try:
                    sizing = fixed_fractional_position_size(
                        equity=account.total_equity(),
                        cash=broker.cash,
                        entry_price=next_open * (1 + slippage_bps / 10_000),
                        stop_loss=intent.stop_loss,
                        risk_per_trade_pct=intent.risk_fraction_pct or risk_per_trade_pct,
                        fee_bps=fee_bps,
                        max_total_exposure_pct=max_total_exposure_pct,
                        min_stop_distance_bps=min_stop_distance_bps,
                        max_stop_distance_pct=max_stop_distance_pct,
                    )
                except ValueError:
                    broker.orders.append(
                        _rejected_order_row(symbol, timestamp, next_open, "risk_rejected")
                    )
                else:
                    broker.submit_order(
                        OrderRequest(
                            symbol=symbol,
                            side=OrderSide.BUY,
                            quantity=sizing.quantity,
                            stop_loss=intent.stop_loss,
                            take_profit=intent.take_profit,
                            reason=intent.reason,
                        ),
                        timestamp=timestamp,
                        next_open=next_open,
                    )
            elif intent.action in {"SELL", "EXIT"} and broker.position is not None:
                broker.submit_order(
                    OrderRequest(
                        symbol=symbol,
                        side=OrderSide.SELL,
                        quantity=broker.position.quantity,
                        reason=intent.reason,
                    ),
                    timestamp=timestamp,
                    next_open=next_open,
                )

        mark_price = float(next_row["close"]) if mark_to_market else next_open
        account_after = broker.account_state(mark_price=mark_price)
        equity_rows.append(
            {
                "timestamp": timestamp,
                "equity": account_after.total_equity(),
                "cash": account_after.cash,
                "position_quantity": (
                    account_after.position.quantity if account_after.position else 0.0
                ),
                "in_position": account_after.position is not None,
            }
        )

    if broker.position is not None:
        final_row = candles_df.iloc[-1]
        broker.submit_order(
            OrderRequest(
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=broker.position.quantity,
                reason="strategy_exit",
            ),
            timestamp=final_row["timestamp"],
            next_open=float(final_row["open"]),
        )
        account_after = broker.account_state(mark_price=float(final_row["close"]))
        equity_rows.append(
            {
                "timestamp": final_row["timestamp"],
                "equity": account_after.total_equity(),
                "cash": account_after.cash,
                "position_quantity": 0.0,
                "in_position": False,
            }
        )

    equity_curve = pd.DataFrame(equity_rows)
    trades = pd.DataFrame([asdict(trade) for trade in broker.trades])
    orders = pd.DataFrame([asdict(order) for order in broker.orders])
    metrics = calculate_metrics(
        equity_curve=equity_curve,
        trades=trades,
        orders=orders,
        starting_equity=starting_equity,
    )
    selected_run_id = run_id or new_run_id()
    metadata = {
        "run_id": selected_run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "exchange": exchange,
        "symbol": symbol,
        "timeframe": timeframe,
        "strategy": strategy.name,
        "data_first_timestamp": candles[0].timestamp.isoformat(),
        "data_last_timestamp": candles[-1].timestamp.isoformat(),
        "data_rows": len(candles),
        "fees_bps": fee_bps,
        "slippage_bps": slippage_bps,
        "strategy_params": getattr(strategy, "__dict__", {}),
        "live_trading": False,
    }
    output_dir = Path(output_root) / selected_run_id
    if write_artifacts:
        output_dir = write_backtest_artifacts(
            output_root=output_root,
            run_id=selected_run_id,
            config_snapshot=config_snapshot,
            metrics=metrics,
            equity_curve=equity_curve,
            trades=trades,
            orders=orders,
            metadata=metadata,
        )
    return BacktestResult(
        run_id=selected_run_id,
        output_dir=output_dir,
        metrics=metrics,
        equity_curve=equity_curve,
        trades=trades,
        orders=orders,
        metadata=metadata,
    )


def _rejected_order_row(symbol: str, timestamp: datetime, price: float, reason: str) -> Any:
    from trading_bot.backtesting.events import OrderRecord, OrderStatus

    return OrderRecord(
        timestamp=timestamp,
        symbol=symbol,
        side=OrderSide.BUY,
        quantity=0,
        requested_price=price,
        fill_price=None,
        status=OrderStatus.REJECTED,
        reason=reason,
    )

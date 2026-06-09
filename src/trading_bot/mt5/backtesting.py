from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from trading_bot.backtesting.metrics import calculate_metrics
from trading_bot.backtesting.results import BacktestResult, new_run_id, write_backtest_artifacts
from trading_bot.mt5.cache import Mt5RatesCache
from trading_bot.mt5.data import Mt5RateBar, validate_mt5_bars
from trading_bot.ny_session.models import NySessionSignal
from trading_bot.ny_session.strategies import get_ny_session_strategy


class Mt5BacktestError(RuntimeError):
    """Raised when MT5 research backtesting cannot run."""


@dataclass(frozen=True)
class Mt5BacktestMarketModel:
    starting_equity: float = 10_000
    risk_per_trade_pct: float = 0.25
    fee_bps: float = 0
    slippage_points: float = 0
    point_value: float = 1
    min_lot: float = 0.01
    lot_step: float = 0.01
    max_lot: float = 100
    min_stop_distance_points: float = 0
    allow_shorting: bool = False


@dataclass
class Mt5BacktestPosition:
    side: str
    quantity: float
    entry_price: float
    stop_loss: float
    entry_timestamp: datetime
    entry_fee: float


def run_mt5_backtest_from_cache(
    *,
    cache_dir: str | Path,
    output_root: str | Path,
    broker: str,
    symbol: str,
    timeframe: str,
    strategy_name: str,
    strategy_params: dict[str, object] | None = None,
    market_model: Mt5BacktestMarketModel | None = None,
    config_snapshot: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> BacktestResult:
    cache = Mt5RatesCache(cache_dir)
    cache_path = cache.path_for(broker, symbol, timeframe)
    if not cache_path.exists():
        raise Mt5BacktestError(f"missing MT5 cache file: {cache_path}")
    bars = cache.read(broker, symbol, timeframe)
    if len(bars) < 2:
        raise Mt5BacktestError("at least two MT5 bars are required")
    validate_mt5_bars(bars, timeframe, validate_continuity=True)
    strategy = get_ny_session_strategy(strategy_name, strategy_params)
    return run_mt5_backtest_on_bars(
        bars=bars,
        output_root=output_root,
        broker=broker,
        symbol=symbol,
        timeframe=timeframe,
        strategy=strategy,
        market_model=market_model or Mt5BacktestMarketModel(),
        config_snapshot=config_snapshot or {},
        run_id=run_id,
        write_artifacts=True,
    )


def run_mt5_backtest_on_bars(
    *,
    bars: list[Mt5RateBar],
    output_root: str | Path,
    broker: str,
    symbol: str,
    timeframe: str,
    strategy: Any,
    market_model: Mt5BacktestMarketModel,
    config_snapshot: dict[str, Any],
    trade_start_index: int = 0,
    run_id: str | None = None,
    write_artifacts: bool = False,
) -> BacktestResult:
    if market_model.starting_equity <= 0:
        raise Mt5BacktestError("starting equity must be positive")
    dataframe = _bars_to_dataframe(bars)
    cash = market_model.starting_equity
    position: Mt5BacktestPosition | None = None
    orders: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []

    for index in range(len(dataframe) - 1):
        next_row = dataframe.iloc[index + 1]
        timestamp = next_row["timestamp"]
        next_open = float(next_row["open"])
        in_trade_period = index + 1 >= trade_start_index

        if in_trade_period and position is not None and _stop_touched(position, next_row):
            cash, position = _close_position(
                cash=cash,
                position=position,
                exit_price=position.stop_loss,
                timestamp=timestamp,
                symbol=symbol,
                reason="stop_loss",
                market_model=market_model,
                orders=orders,
                trades=trades,
            )
        if in_trade_period and position is None:
            signal = strategy.generate_signal(dataframe.iloc[: index + 1], index)
            if signal.signal == NySessionSignal.ENTER_LONG:
                position, cash = _open_position(
                    cash=cash,
                    side="LONG",
                    entry_price=next_open + market_model.slippage_points,
                    stop_loss=signal.stop_loss,
                    timestamp=timestamp,
                    symbol=symbol,
                    reason=signal.reason,
                    market_model=market_model,
                    orders=orders,
                )
            elif signal.signal == NySessionSignal.ENTER_SHORT:
                if market_model.allow_shorting:
                    position, cash = _open_position(
                        cash=cash,
                        side="SHORT",
                        entry_price=next_open - market_model.slippage_points,
                        stop_loss=signal.stop_loss,
                        timestamp=timestamp,
                        symbol=symbol,
                        reason=signal.reason,
                        market_model=market_model,
                        orders=orders,
                    )
                else:
                    orders.append(
                        _order_row(
                            timestamp=timestamp,
                            symbol=symbol,
                            side="SELL",
                            quantity=0,
                            requested_price=next_open,
                            fill_price=None,
                            status="REJECTED",
                            reason="shorting_disabled_for_research_run",
                        )
                    )
        elif in_trade_period and position is not None:
            signal = strategy.generate_signal(
                dataframe.iloc[: index + 1],
                index,
                has_position=True,
            )
            if signal.signal in {NySessionSignal.EXIT, NySessionSignal.SESSION_CLOSE}:
                cash, position = _close_position(
                    cash=cash,
                    position=position,
                    exit_price=next_open,
                    timestamp=timestamp,
                    symbol=symbol,
                    reason=signal.reason,
                    market_model=market_model,
                    orders=orders,
                    trades=trades,
                )

        if in_trade_period:
            equity_rows.append(
                {
                    "timestamp": timestamp,
                    "equity": _equity(cash, position, float(next_row["close"]), market_model),
                    "cash": cash,
                    "position_quantity": position.quantity if position else 0,
                    "in_position": position is not None,
                }
            )

    if position is not None:
        final_row = dataframe.iloc[-1]
        cash, position = _close_position(
            cash=cash,
            position=position,
            exit_price=float(final_row["close"]),
            timestamp=final_row["timestamp"],
            symbol=symbol,
            reason="final_bar_exit",
            market_model=market_model,
            orders=orders,
            trades=trades,
        )
        equity_rows.append(
            {
                "timestamp": final_row["timestamp"],
                "equity": cash,
                "cash": cash,
                "position_quantity": 0,
                "in_position": False,
            }
        )

    equity_curve = pd.DataFrame(equity_rows)
    trades_frame = pd.DataFrame(trades)
    orders_frame = pd.DataFrame(orders)
    metrics = calculate_metrics(
        equity_curve=equity_curve,
        trades=trades_frame,
        orders=orders_frame,
        starting_equity=market_model.starting_equity,
    )
    selected_run_id = run_id or f"mt5_backtest_{new_run_id()}"
    metadata = {
        "run_id": selected_run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "broker": broker,
        "symbol": symbol,
        "timeframe": timeframe,
        "strategy": strategy.name,
        "data_first_timestamp": bars[0].timestamp.isoformat(),
        "data_last_timestamp": bars[-1].timestamp.isoformat(),
        "data_rows": len(bars),
        "market_model": market_model.__dict__,
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
    }
    output_dir = Path(output_root) / selected_run_id
    if write_artifacts:
        output_dir = write_backtest_artifacts(
            output_root=output_root,
            run_id=selected_run_id,
            config_snapshot=config_snapshot,
            metrics=metrics,
            equity_curve=equity_curve,
            trades=trades_frame,
            orders=orders_frame,
            metadata=metadata,
        )
    return BacktestResult(
        run_id=selected_run_id,
        output_dir=output_dir,
        metrics=metrics,
        equity_curve=equity_curve,
        trades=trades_frame,
        orders=orders_frame,
        metadata=metadata,
    )


def _open_position(
    *,
    cash: float,
    side: str,
    entry_price: float,
    stop_loss: float | None,
    timestamp: datetime,
    symbol: str,
    reason: str,
    market_model: Mt5BacktestMarketModel,
    orders: list[dict[str, Any]],
) -> tuple[Mt5BacktestPosition | None, float]:
    if stop_loss is None:
        orders.append(_rejection(timestamp, symbol, side, entry_price, "missing_stop_loss"))
        return None, cash
    stop_distance = abs(entry_price - stop_loss)
    if stop_distance <= market_model.min_stop_distance_points:
        orders.append(_rejection(timestamp, symbol, side, entry_price, "invalid_stop_distance"))
        return None, cash
    risk_amount = cash * market_model.risk_per_trade_pct / 100
    quantity = _round_lot(risk_amount / (stop_distance * market_model.point_value), market_model)
    if quantity <= 0:
        orders.append(_rejection(timestamp, symbol, side, entry_price, "invalid_lot_size"))
        return None, cash
    fee = _fee(entry_price, quantity, market_model)
    cash_after = cash - fee
    orders.append(
        _order_row(
            timestamp=timestamp,
            symbol=symbol,
            side="BUY" if side == "LONG" else "SELL",
            quantity=quantity,
            requested_price=entry_price,
            fill_price=entry_price,
            status="FILLED",
            reason=reason,
            fee=fee,
            slippage_paid_estimate=market_model.slippage_points * quantity,
        )
    )
    return (
        Mt5BacktestPosition(
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            entry_timestamp=timestamp,
            entry_fee=fee,
        ),
        cash_after,
    )


def _close_position(
    *,
    cash: float,
    position: Mt5BacktestPosition,
    exit_price: float,
    timestamp: datetime,
    symbol: str,
    reason: str,
    market_model: Mt5BacktestMarketModel,
    orders: list[dict[str, Any]],
    trades: list[dict[str, Any]],
) -> tuple[float, None]:
    fill_price = (
        exit_price - market_model.slippage_points
        if position.side == "LONG"
        else exit_price + market_model.slippage_points
    )
    pnl = _position_pnl(position, fill_price, market_model)
    fee = _fee(fill_price, position.quantity, market_model)
    cash_after = cash + pnl - fee
    orders.append(
        _order_row(
            timestamp=timestamp,
            symbol=symbol,
            side="SELL" if position.side == "LONG" else "BUY",
            quantity=position.quantity,
            requested_price=exit_price,
            fill_price=fill_price,
            status="FILLED",
            reason=reason,
            fee=fee,
            slippage_paid_estimate=market_model.slippage_points * position.quantity,
        )
    )
    trades.append(
        {
            "entry_timestamp": position.entry_timestamp,
            "exit_timestamp": timestamp,
            "symbol": symbol,
            "quantity": position.quantity,
            "entry_price": position.entry_price,
            "exit_price": fill_price,
            "pnl": pnl - position.entry_fee - fee,
            "fees": position.entry_fee + fee,
            "reason": reason,
        }
    )
    return cash_after, None


def _stop_touched(position: Mt5BacktestPosition, row: pd.Series) -> bool:
    if position.side == "LONG":
        return float(row["low"]) <= position.stop_loss
    return float(row["high"]) >= position.stop_loss


def _position_pnl(
    position: Mt5BacktestPosition,
    mark_price: float,
    market_model: Mt5BacktestMarketModel,
) -> float:
    direction = 1 if position.side == "LONG" else -1
    return (
        (mark_price - position.entry_price)
        * direction
        * position.quantity
        * market_model.point_value
    )


def _equity(
    cash: float,
    position: Mt5BacktestPosition | None,
    mark_price: float,
    market_model: Mt5BacktestMarketModel,
) -> float:
    if position is None:
        return cash
    return cash + _position_pnl(position, mark_price, market_model)


def _fee(price: float, quantity: float, market_model: Mt5BacktestMarketModel) -> float:
    return abs(price * quantity * market_model.point_value) * market_model.fee_bps / 10_000


def _round_lot(quantity: float, market_model: Mt5BacktestMarketModel) -> float:
    if quantity < market_model.min_lot:
        return 0
    steps = int(quantity / market_model.lot_step)
    rounded = steps * market_model.lot_step
    return min(round(rounded, 8), market_model.max_lot)


def _rejection(
    timestamp: datetime,
    symbol: str,
    side: str,
    price: float,
    reason: str,
) -> dict[str, Any]:
    return _order_row(
        timestamp=timestamp,
        symbol=symbol,
        side="BUY" if side == "LONG" else "SELL",
        quantity=0,
        requested_price=price,
        fill_price=None,
        status="REJECTED",
        reason=reason,
    )


def _order_row(
    *,
    timestamp: datetime,
    symbol: str,
    side: str,
    quantity: float,
    requested_price: float,
    fill_price: float | None,
    status: str,
    reason: str,
    fee: float = 0,
    slippage_paid_estimate: float = 0,
) -> dict[str, Any]:
    return {
        "timestamp": timestamp,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "requested_price": requested_price,
        "fill_price": fill_price,
        "status": status,
        "reason": reason,
        "fee": fee,
        "slippage_paid_estimate": slippage_paid_estimate,
    }


def _bars_to_dataframe(bars: list[Mt5RateBar]) -> pd.DataFrame:
    dataframe = pd.DataFrame([bar.model_dump() for bar in bars])
    dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], utc=True)
    dataframe["new_york_timestamp"] = pd.to_datetime(
        dataframe["new_york_timestamp"],
        utc=True,
    ).dt.tz_convert("America/New_York")
    return dataframe

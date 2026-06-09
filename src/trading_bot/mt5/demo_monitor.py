from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from trading_bot.mt5.data import Mt5RateBar
from trading_bot.ny_session.models import NySessionSignal
from trading_bot.ny_session.strategies import get_ny_session_strategy
from trading_bot.paper.store import append_jsonl
from trading_bot.risk.kill_switch import KillSwitch


class Mt5DemoMonitorError(RuntimeError):
    """Raised when the MT5 demo monitor cannot continue safely."""


PYTHON_MT5_EXECUTION_QUARANTINED_REASON = "python_mt5_execution_quarantined"


class Mt5DemoPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    side: str
    volume: float
    entry_price: float
    stop_loss: float
    take_profit: float | None = None
    opened_at: datetime


class Mt5DemoMonitorState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monitor_run_id: str
    created_at: datetime
    updated_at: datetime
    broker: str
    symbol: str
    timeframe: str
    strategy: str
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    demo_orders: list[dict[str, Any]] = Field(default_factory=list)
    health_events: list[dict[str, Any]] = Field(default_factory=list)
    open_position: Mt5DemoPosition | None = None
    last_processed_candle_timestamp: datetime | None = None
    kill_switch_active: bool = False
    consecutive_order_errors: int = 0


class Mt5DemoMonitorStore:
    def __init__(self, state_dir: str | Path = "data/processed/mt5_demo_monitor") -> None:
        self.state_dir = Path(state_dir)

    def run_dir(self, monitor_run_id: str) -> Path:
        return self.state_dir / monitor_run_id

    def save(self, state: Mt5DemoMonitorState, metadata: dict[str, Any]) -> None:
        run_dir = self.run_dir(state.monitor_run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        state_path = run_dir / "state.json"
        tmp_path = state_path.with_suffix(".json.tmp")
        tmp_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp_path, state_path)
        pd.DataFrame(state.decisions).to_parquet(run_dir / "decisions.parquet", index=False)
        pd.DataFrame(state.demo_orders).to_parquet(run_dir / "demo_orders.parquet", index=False)
        pd.DataFrame(state.health_events).to_parquet(
            run_dir / "health_events.parquet",
            index=False,
        )
        (run_dir / "run_metadata.json").write_text(
            json.dumps(_json_safe(metadata), indent=2),
            encoding="utf-8",
        )

    def load(self, monitor_run_id: str) -> Mt5DemoMonitorState:
        path = self.run_dir(monitor_run_id) / "state.json"
        if not path.exists():
            raise ValueError(f"missing MT5 demo monitor state: {path}")
        return Mt5DemoMonitorState.model_validate_json(path.read_text(encoding="utf-8"))


def new_mt5_demo_monitor_state(
    *,
    broker: str,
    symbol: str,
    timeframe: str,
    strategy: str,
    monitor_run_id: str | None = None,
) -> Mt5DemoMonitorState:
    now = datetime.now(UTC)
    return Mt5DemoMonitorState(
        monitor_run_id=monitor_run_id
        or f"mt5_demo_monitor_{now.strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}",
        created_at=now,
        updated_at=now,
        broker=broker,
        symbol=symbol,
        timeframe=timeframe,
        strategy=strategy,
    )


def run_mt5_demo_monitor_once(
    *,
    state: Mt5DemoMonitorState,
    bars: list[Mt5RateBar],
    execution_client: Any | None = None,
    max_spread_points: int = 30,
    max_consecutive_order_errors: int = 3,
    decision_log_dir: str | Path = "data/processed/mt5_demo_monitor/decisions",
) -> Mt5DemoMonitorState:
    if not bars:
        raise Mt5DemoMonitorError("no MT5 bars available for demo monitor")
    latest = bars[-1]
    if state.last_processed_candle_timestamp == latest.timestamp:
        _health(state, "DUPLICATE_CANDLE", "latest candle already processed")
        return _save_update(state)
    kill_switch = KillSwitch(armed=True)
    kill_switch.check_repeated_order_errors(
        error_count=state.consecutive_order_errors,
        max_errors=max_consecutive_order_errors,
    )
    if kill_switch.state.shutdown:
        state.kill_switch_active = True
        _health(state, "KILL_SWITCH_ACTIVE", kill_switch.state.reason or "shutdown")
        return _save_update(state)
    if _handle_protective_exit(state, latest, execution_client, decision_log_dir):
        state.last_processed_candle_timestamp = latest.timestamp
        return _save_update(state)

    strategy = get_ny_session_strategy(state.strategy, {"max_spread": max_spread_points})
    dataframe = _bars_to_dataframe(bars)
    signal = strategy.generate_signal(
        dataframe,
        len(dataframe) - 1,
        has_position=state.open_position is not None,
    )
    decision = {
        "timestamp": latest.timestamp,
        "symbol": state.symbol,
        "strategy": state.strategy,
        "signal": signal.signal.value,
        "reason": signal.reason,
        "stop_loss": signal.stop_loss,
        "take_profit": signal.take_profit,
        "demo_execution_enabled": False,
        "python_mt5_execution_quarantined": execution_client is not None,
    }
    state.decisions.append(decision)
    append_jsonl(
        Path(decision_log_dir) / state.monitor_run_id / "decisions.jsonl",
        decision,
    )

    if signal.signal in {NySessionSignal.SKIP_NEWS, NySessionSignal.SKIP_SPREAD}:
        _health(state, signal.signal.value, signal.reason)
    elif signal.signal in {NySessionSignal.ENTER_LONG, NySessionSignal.ENTER_SHORT}:
        _handle_entry(state, latest, signal, execution_client)
    elif signal.signal in {NySessionSignal.EXIT, NySessionSignal.SESSION_CLOSE}:
        _handle_exit(state, latest, signal, execution_client)

    state.last_processed_candle_timestamp = latest.timestamp
    return _save_update(state)


def _handle_entry(
    state: Mt5DemoMonitorState,
    latest: Mt5RateBar,
    signal: Any,
    execution_client: Any | None,
) -> None:
    if state.open_position is not None:
        _health(state, "ENTRY_SKIPPED", "position_already_open")
        return
    if signal.stop_loss is None:
        _health(state, "ENTRY_REJECTED", "missing_stop_loss")
        return
    side = "BUY" if signal.signal == NySessionSignal.ENTER_LONG else "SELL"
    if execution_client is not None:
        _health(state, "PYTHON_MT5_EXECUTION_QUARANTINED", PYTHON_MT5_EXECUTION_QUARANTINED_REASON)
    _health(state, "ENTRY_OBSERVED", f"{side.lower()}_signal_monitor_only")


def _handle_exit(
    state: Mt5DemoMonitorState,
    latest: Mt5RateBar,
    signal: Any,
    execution_client: Any | None,
) -> None:
    if state.open_position is None:
        return
    close_side = "SELL" if state.open_position.side == "BUY" else "BUY"
    if execution_client is not None:
        _health(state, "PYTHON_MT5_EXECUTION_QUARANTINED", PYTHON_MT5_EXECUTION_QUARANTINED_REASON)
    _health(state, "EXIT_OBSERVED", f"{close_side.lower()}_close_signal_monitor_only")


def _handle_protective_exit(
    state: Mt5DemoMonitorState,
    latest: Mt5RateBar,
    execution_client: Any | None,
    decision_log_dir: str | Path,
) -> bool:
    position = state.open_position
    if position is None:
        return False
    trigger = _protective_trigger(position, latest)
    if trigger is None:
        return False
    decision = {
        "timestamp": latest.timestamp,
        "symbol": state.symbol,
        "strategy": state.strategy,
        "signal": "PROTECTIVE_EXIT",
        "reason": trigger["reason"],
        "stop_loss": position.stop_loss,
        "take_profit": position.take_profit,
        "demo_execution_enabled": False,
        "python_mt5_execution_quarantined": execution_client is not None,
    }
    state.decisions.append(decision)
    append_jsonl(
        Path(decision_log_dir) / state.monitor_run_id / "decisions.jsonl",
        decision,
    )
    if execution_client is not None:
        _health(state, "PYTHON_MT5_EXECUTION_QUARANTINED", PYTHON_MT5_EXECUTION_QUARANTINED_REASON)
    _health(state, "PROTECTIVE_EXIT_OBSERVED", str(trigger["reason"]))
    return True


def _protective_trigger(
    position: Mt5DemoPosition,
    latest: Mt5RateBar,
) -> dict[str, str | float] | None:
    if position.side == "BUY":
        if latest.low <= position.stop_loss:
            return {"reason": "stop_loss_touched", "price": position.stop_loss}
        if position.take_profit is not None and latest.high >= position.take_profit:
            return {"reason": "take_profit_touched", "price": position.take_profit}
    if position.side == "SELL":
        if latest.high >= position.stop_loss:
            return {"reason": "stop_loss_touched", "price": position.stop_loss}
        if position.take_profit is not None and latest.low <= position.take_profit:
            return {"reason": "take_profit_touched", "price": position.take_profit}
    return None


def _health(state: Mt5DemoMonitorState, code: str, message: str) -> None:
    state.health_events.append(
        {
            "timestamp": datetime.now(UTC),
            "code": code,
            "message": message,
        }
    )


def _save_update(state: Mt5DemoMonitorState) -> Mt5DemoMonitorState:
    state.updated_at = datetime.now(UTC)
    return state


def _bars_to_dataframe(bars: list[Mt5RateBar]) -> pd.DataFrame:
    dataframe = pd.DataFrame([bar.model_dump() for bar in bars])
    dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], utc=True)
    dataframe["new_york_timestamp"] = pd.to_datetime(
        dataframe["new_york_timestamp"],
        utc=True,
    ).dt.tz_convert("America/New_York")
    return dataframe


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value

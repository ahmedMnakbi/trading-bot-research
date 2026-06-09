from datetime import UTC, datetime, timedelta
from pathlib import Path

from trading_bot.mt5.data import rates_to_bars
from trading_bot.mt5.demo_monitor import (
    Mt5DemoMonitorStore,
    Mt5DemoPosition,
    new_mt5_demo_monitor_state,
    run_mt5_demo_monitor_once,
)


class AcceptingExecutionClient:
    def __init__(self) -> None:
        self.requests = []

    def submit_demo_order(self, request):
        self.requests.append(request)


def _bars(rows: int = 80):
    start = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)
    raw = []
    price = 100.0
    for index in range(rows):
        timestamp = start + timedelta(minutes=5 * index)
        price += 0.25
        raw.append(
            {
                "time": int(timestamp.timestamp()),
                "open": price - 0.1,
                "high": price + 0.6,
                "low": price - 0.6,
                "close": price,
                "tick_volume": float(100 + index),
                "spread": 10,
            }
        )
    return rates_to_bars(raw)


def test_demo_monitor_logs_decision_without_execution(tmp_path: Path) -> None:
    state = new_mt5_demo_monitor_state(
        broker="demo_broker",
        symbol="EURUSD",
        timeframe="5m",
        strategy="vwap_trend_continuation",
        monitor_run_id="monitor_fixture",
    )

    updated = run_mt5_demo_monitor_once(
        state=state,
        bars=_bars(),
        decision_log_dir=tmp_path / "decisions",
    )

    assert len(updated.decisions) == 1
    assert updated.demo_orders == []
    assert (tmp_path / "decisions" / "monitor_fixture" / "decisions.jsonl").exists()


def test_demo_monitor_quarantines_python_execution_client_when_configured() -> None:
    state = new_mt5_demo_monitor_state(
        broker="demo_broker",
        symbol="EURUSD",
        timeframe="5m",
        strategy="vwap_trend_continuation",
    )
    client = AcceptingExecutionClient()

    updated = run_mt5_demo_monitor_once(state=state, bars=_bars(), execution_client=client)

    assert client.requests == []
    assert updated.demo_orders == []
    assert updated.open_position is None
    assert updated.decisions[-1]["demo_execution_enabled"] is False
    assert updated.decisions[-1]["python_mt5_execution_quarantined"] is True
    assert any(
        event["code"] == "PYTHON_MT5_EXECUTION_QUARANTINED"
        for event in updated.health_events
    )


def test_demo_monitor_tracks_order_errors_and_kill_switch() -> None:
    state = new_mt5_demo_monitor_state(
        broker="demo_broker",
        symbol="EURUSD",
        timeframe="5m",
        strategy="vwap_trend_continuation",
    )
    state.consecutive_order_errors = 3

    updated = run_mt5_demo_monitor_once(
        state=state,
        bars=_bars(),
    )

    assert updated.kill_switch_active is True
    assert updated.health_events[-1]["code"] == "KILL_SWITCH_ACTIVE"


def test_demo_monitor_observes_protective_stop_without_execution(tmp_path: Path) -> None:
    bars = _bars()
    latest = bars[-1]
    state = new_mt5_demo_monitor_state(
        broker="demo_broker",
        symbol="EURUSD",
        timeframe="5m",
        strategy="vwap_trend_continuation",
        monitor_run_id="protective_observed",
    )
    state.open_position = Mt5DemoPosition(
        symbol="EURUSD",
        side="BUY",
        volume=0.01,
        entry_price=latest.close,
        stop_loss=latest.low,
        take_profit=None,
        opened_at=latest.timestamp - timedelta(minutes=5),
    )

    updated = run_mt5_demo_monitor_once(
        state=state,
        bars=bars,
        decision_log_dir=tmp_path / "decisions",
    )

    assert updated.open_position is not None
    assert updated.decisions[-1]["signal"] == "PROTECTIVE_EXIT"
    assert updated.health_events[-1]["code"] == "PROTECTIVE_EXIT_OBSERVED"
    assert (tmp_path / "decisions" / "protective_observed" / "decisions.jsonl").exists()


def test_demo_monitor_quarantines_protective_take_profit_execution_client() -> None:
    bars = _bars()
    latest = bars[-1]
    state = new_mt5_demo_monitor_state(
        broker="demo_broker",
        symbol="EURUSD",
        timeframe="5m",
        strategy="vwap_trend_continuation",
    )
    state.open_position = Mt5DemoPosition(
        symbol="EURUSD",
        side="BUY",
        volume=0.02,
        entry_price=latest.close - 1.0,
        stop_loss=latest.close - 2.0,
        take_profit=latest.high,
        opened_at=latest.timestamp - timedelta(minutes=5),
    )
    client = AcceptingExecutionClient()

    updated = run_mt5_demo_monitor_once(
        state=state,
        bars=bars,
        execution_client=client,
    )

    assert updated.open_position is not None
    assert client.requests == []
    assert updated.demo_orders == []
    assert any(
        event["code"] == "PYTHON_MT5_EXECUTION_QUARANTINED"
        for event in updated.health_events
    )
    assert updated.health_events[-1]["code"] == "PROTECTIVE_EXIT_OBSERVED"


def test_demo_monitor_store_persists_state(tmp_path: Path) -> None:
    state = new_mt5_demo_monitor_state(
        broker="demo_broker",
        symbol="EURUSD",
        timeframe="5m",
        strategy="vwap_trend_continuation",
        monitor_run_id="monitor_store_fixture",
    )
    state = run_mt5_demo_monitor_once(state=state, bars=_bars())
    store = Mt5DemoMonitorStore(tmp_path)

    store.save(state, {"live_trading": False, "real_orders_enabled": False})
    loaded = store.load("monitor_store_fixture")

    assert loaded.monitor_run_id == "monitor_store_fixture"
    assert len(loaded.decisions) == 1
    assert (tmp_path / "monitor_store_fixture" / "state.json").exists()

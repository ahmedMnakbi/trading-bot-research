from __future__ import annotations

from trading_bot.risk.kill_switch import KillSwitch


def test_kill_switch_defaults_to_armed() -> None:
    kill_switch = KillSwitch()

    assert kill_switch.state.armed is True
    assert kill_switch.state.shutdown is False


def test_drawdown_triggers_shutdown_state() -> None:
    state = KillSwitch().check_drawdown(current_drawdown_pct=10, max_drawdown_pct=10)

    assert state.shutdown is True
    assert state.reason == "max_drawdown_exceeded"


def test_stale_data_triggers_shutdown_state() -> None:
    state = KillSwitch().check_stale_data(stale_data=True)

    assert state.shutdown is True
    assert state.reason == "stale_data"


def test_repeated_order_errors_trigger_shutdown_state() -> None:
    state = KillSwitch().check_repeated_order_errors(error_count=3, max_errors=3)

    assert state.shutdown is True
    assert state.reason == "repeated_order_errors"


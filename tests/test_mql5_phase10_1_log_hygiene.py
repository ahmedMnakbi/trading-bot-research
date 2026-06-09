from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MQL5_ROOT = ROOT / "mql5"
EA_SOURCE = (
    MQL5_ROOT
    / "Experts"
    / "UpcomersNYSessionPropBot"
    / "UpcomersNYSessionPropBot.mq5"
)
INCLUDE_ROOT = MQL5_ROOT / "Include" / "UpcomersNYSessionPropBot"


def _ea_text() -> str:
    return EA_SOURCE.read_text(encoding="utf-8")


def _include_text(name: str) -> str:
    return (INCLUDE_ROOT / name).read_text(encoding="utf-8")


def _all_mql5_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in MQL5_ROOT.rglob("*.mq*"))


def _input_value(name: str) -> str:
    match = re.search(rf"input\s+\w+(?:_\w+)*\s+{name}\s*=\s*([^;]+);", _ea_text())
    assert match, f"missing input {name}"
    return match.group(1).strip()


def test_log_throttle_skips_defaults_off() -> None:
    ea_text = _ea_text()
    config_text = _include_text("Config.mqh")
    audit_text = _include_text("AuditLogger.mqh")

    assert _input_value("LogThrottleSkips") == "false"
    assert "bool LogThrottleSkips;" in config_text
    assert "g_config.LogThrottleSkips = LogThrottleSkips;" in ea_text
    assert "LogThrottleSkips=%s" in audit_text


def test_routine_throttle_skip_logging_is_suppressible_without_changing_throttle() -> None:
    ea_text = _ea_text()
    state_text = _include_text("StateManager.mqh")

    assert "ShouldEvaluateMonitorEvent" in state_text
    assert "THROTTLE_MIN_SECONDS" in state_text
    assert "m_monitorEvaluationsThrottled++" in state_text
    assert "if(g_config.LogThrottleSkips)\n         g_logger.Info(\"Throttle\", reason);" in ea_text
    assert "g_state.MarkMonitorEvaluation(closedBarTime);" in ea_text


def test_trade_manager_warnings_are_limited_to_actionable_intents() -> None:
    ea_text = _ea_text()
    trade_manager_text = _include_text("TradeManager.mqh")

    assert (
        "bool actionableIntent = g_messageCounter.IsActionableIntent(decision.Signal);"
        in ea_text
    )
    assert "if(actionableIntent)\n         g_logger.Warn(\"TradeManager\", reason);" in ea_text
    assert "NO_ACTION Phase 10.1 monitor TradeManager for non-actionable signal" in (
        trade_manager_text
    )
    non_actionable_section = trade_manager_text.split("messageCounter.RecordTradeIntentEvent()")[0]
    assert "REFUSED Phase 9 no-trade TradeManager" not in non_actionable_section
    assert "WAIT/skip/setup evaluations do not count as trade attempts or server messages" in (
        non_actionable_section
    )


def test_order_placement_calls_are_isolated_to_execution_modules() -> None:
    assert "OrderSend(request, result)" in _include_text("TrialExecution.mqh")
    assert "OrderSend(request, result)" in _include_text("TesterExecution.mqh")
    for path in MQL5_ROOT.rglob("*"):
        if path.suffix.lower() not in {".mq5", ".mqh"} or path.name in {
            "TrialExecution.mqh",
            "TesterExecution.mqh",
        }:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in [
            "OrderSend",
            "CTrade",
            ".Buy(",
            ".Sell(",
            "PositionOpen",
            "BuyLimit",
            "SellLimit",
            "BuyStop",
            "SellStop",
        ]:
            assert pattern not in text


def test_ea_remains_monitor_only() -> None:
    ea_text = _ea_text()
    trade_manager_text = _include_text("TradeManager.mqh")

    assert _input_value("EnableTrading") == "false"
    assert _input_value("EnableTrialExecution") == "false"
    assert _input_value("EnablePropChallengeMode") == "false"
    assert "Monitor-only mode is active" in ea_text
    assert "return false" in trade_manager_text

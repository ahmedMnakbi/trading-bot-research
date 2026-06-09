from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from trading_bot.mql5.models import ApprovalMetadata
from trading_bot.mql5.settings import (
    TRIAL_EXECUTION_MANUAL_CONFIRMATION,
    EaSettingsError,
    build_settings,
)
from trading_bot.mql5.source_scan import scan_mql5_source_tree
from trading_bot.mt5.safety import find_mt5_prohibited_patterns

ROOT = Path(__file__).resolve().parents[1]
MQL5_ROOT = ROOT / "mql5"
EA_SOURCE = (
    MQL5_ROOT
    / "Experts"
    / "UpcomersNYSessionPropBot"
    / "UpcomersNYSessionPropBot.mq5"
)
INCLUDE_ROOT = MQL5_ROOT / "Include" / "UpcomersNYSessionPropBot"
TRIAL_EXECUTION = INCLUDE_ROOT / "TrialExecution.mqh"
CONFIG = INCLUDE_ROOT / "Config.mqh"


def _ea_text() -> str:
    return EA_SOURCE.read_text(encoding="utf-8")


def _trial_text() -> str:
    return TRIAL_EXECUTION.read_text(encoding="utf-8")


def _config_text() -> str:
    return CONFIG.read_text(encoding="utf-8")


def _input_value(name: str) -> str:
    match = re.search(rf"input\s+[\w_]+\s+{name}\s*=\s*([^;]+);", _ea_text())
    assert match, f"missing input {name}"
    return match.group(1).strip()


def _trial_execution_overrides(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "enable_trading": True,
        "enable_trial_execution": True,
        "manual_confirmation_text": TRIAL_EXECUTION_MANUAL_CONFIRMATION,
        "broker_time_validation_note": "broker server UTC offset manually verified",
    }
    values.update(overrides)
    return values


def test_defaults_keep_trial_execution_off_and_eurusd_only() -> None:
    assert _input_value("EnableTrading") == "false"
    assert _input_value("EnableTrialExecution") == "false"
    assert _input_value("EnablePropChallengeMode") == "false"
    assert _input_value("AllowedSymbols") == '"EURUSD"'
    assert _input_value("MaxTradesPerDay") == "1"
    assert _input_value("MaxOpenPositionsTotal") == "1"
    assert _input_value("MaxOpenPositionsPerSymbol") == "1"


def test_exact_confirmation_and_source_scan_pass_id_are_required() -> None:
    with pytest.raises(EaSettingsError, match="exact manual confirmation"):
        build_settings(
            overrides=_trial_execution_overrides(manual_confirmation_text="close enough")
        )
    with pytest.raises(EaSettingsError, match="source scan PASS marker"):
        build_settings(overrides=_trial_execution_overrides())

    settings = build_settings(
        overrides=_trial_execution_overrides(),
        approval_metadata=ApprovalMetadata(source_scan_pass_id="mql5-source-scan-pass"),
    )
    assert settings.enable_trial_execution is True


@pytest.mark.parametrize("program", ["Surge2Step", "Vanguard", "Custom"])
def test_trial_execution_rejects_non_trial_risk_free_programs(program: str) -> None:
    with pytest.raises(EaSettingsError, match="TrialRiskFree"):
        build_settings(
            account_program=program,
            overrides=_trial_execution_overrides(),
            approval_metadata=ApprovalMetadata(source_scan_pass_id="scan-pass"),
        )


@pytest.mark.parametrize("stage", ["MonitorOnly", "Challenge", "Verification", "Funded"])
def test_trial_execution_rejects_non_trial_stages(stage: str) -> None:
    with pytest.raises(EaSettingsError, match="AccountStage Trial"):
        build_settings(
            stage=stage,
            overrides=_trial_execution_overrides(),
            approval_metadata=ApprovalMetadata(source_scan_pass_id="scan-pass"),
        )


def test_mql5_config_contains_trial_only_gate_checks() -> None:
    text = _config_text()
    required = [
        "config.AccountProgram != ACCOUNT_PROGRAM_TRIAL_RISK_FREE",
        "config.AccountStage != ACCOUNT_STAGE_TRIAL",
        "config.EnablePropChallengeMode",
        "!HasTrialExecutionConfirmation(config)",
        "!HasText(config.SourceScanPassId)",
        "config.MaxTradesPerDay != 1",
        "config.MaxOpenPositionsTotal != 1 || config.MaxOpenPositionsPerSymbol != 1",
        "!IsTrialExecutionSymbolSetStrict(config.AllowedSymbols)",
    ]
    for snippet in required:
        assert snippet in text


def test_wait_skip_and_setup_forming_are_non_executable_readiness_logs() -> None:
    text = _trial_text()
    non_entry_section = text.split("string gateReason = \"\";")[0]
    assert "decision.Signal != SIGNAL_ENTER_LONG_INTENT" in non_entry_section
    assert "decision.Signal != SIGNAL_ENTER_SHORT_INTENT" in non_entry_section
    assert "NO_ACTION_SIGNAL_NOT_EXECUTABLE signal=SETUP_FORMING" in non_entry_section
    assert "ARMED_TRIAL_EXECUTION_WAITING_FOR_VALID_SIGNAL" in non_entry_section
    assert "OrderSend" not in non_entry_section


def test_only_enter_long_or_short_with_sltp_can_reach_order_send() -> None:
    text = _trial_text()
    order_prefix = text.split("OrderSend(request, result)")[0]
    assert "SIGNAL_ENTER_LONG_INTENT" in order_prefix
    assert "SIGNAL_ENTER_SHORT_INTENT" in order_prefix
    assert "ValidateStopAndTakeProfit(symbol, decision, entryPrice, slTpReason)" in (
        order_prefix
    )
    assert "!decision.HasStopLoss || !decision.HasTakeProfit" in order_prefix
    assert "decision.SuggestedStopLoss <= 0.0 || decision.SuggestedTakeProfit <= 0.0" in (
        order_prefix
    )


def test_sltp_uses_broker_stop_level_metadata_when_available() -> None:
    text = _trial_text()
    required = [
        "SYMBOL_TRADE_STOPS_LEVEL",
        "SYMBOL_POINT",
        "STOP_LEVEL_CONSTRAINT failed",
        "stopDistance < minimumDistance || takeProfitDistance < minimumDistance",
    ]
    for snippet in required:
        assert snippet in text


def test_lot_size_uses_minimum_lot_or_refuses_if_not_safe() -> None:
    text = _trial_text()
    required = [
        "SYMBOL_VOLUME_MIN",
        "SYMBOL_VOLUME_STEP",
        "SYMBOL_TRADE_TICK_SIZE",
        "SYMBOL_TRADE_TICK_VALUE",
        "riskBasedLot < minVolume",
        "broker minimum lot",
        "volume = minVolume",
    ]
    for snippet in required:
        assert snippet in text


def test_one_trade_one_position_and_no_retry_are_enforced() -> None:
    text = _trial_text()
    assert "PositionsTotal()" in text
    assert "CountOpenPositionsForSymbol(symbol)" in text
    assert "messageCounter.TradeIntentEvents() + 1 <= config.MaxTradesPerDay" in text
    assert "messageCounter.ActualServerMessages() + 1 <= config.MaxServerMessagesPerDay" in text
    assert "OneAttemptPerSignal" in text
    assert "NO_RETRY_ORDER_SEND_ONCE" in text
    assert text.count("OrderSend(request, result)") == 1
    assert "while(" not in text
    assert "for(;;" not in text


def test_no_pending_order_calls_or_order_calls_outside_trial_execution() -> None:
    trial_text = _trial_text()
    for forbidden in [
        "ORDER_TYPE_BUY_LIMIT",
        "ORDER_TYPE_SELL_LIMIT",
        "ORDER_TYPE_BUY_STOP",
        "ORDER_TYPE_SELL_STOP",
        "BuyLimit",
        "SellLimit",
        "BuyStop",
        "SellStop",
    ]:
        assert forbidden not in trial_text

    tester_execution = INCLUDE_ROOT / "TesterExecution.mqh"
    for path in MQL5_ROOT.rglob("*"):
        if path.suffix.lower() not in {".mq5", ".mqh"} or path in {
            TRIAL_EXECUTION,
            tester_execution,
        }:
            continue
        text = path.read_text(encoding="utf-8")
        for forbidden in ["OrderSend", "CTrade", ".Buy(", ".Sell(", "PositionOpen"]:
            assert forbidden not in text


def test_source_scan_requires_phase13_1_safety_markers(tmp_path: Path) -> None:
    result = scan_mql5_source_tree(ROOT)
    checks = {check.name: check for check in result.safeguards}
    assert result.status == "PASS"
    assert checks["TrialExecutionOrderGates"].status == "PASS"

    shutil.copytree(MQL5_ROOT, tmp_path / "mql5")
    trial_execution = (
        tmp_path / "mql5" / "Include" / "UpcomersNYSessionPropBot" / "TrialExecution.mqh"
    )
    trial_execution.write_text(
        trial_execution.read_text(encoding="utf-8").replace("SYMBOL_TRADE_STOPS_LEVEL", ""),
        encoding="utf-8",
    )
    unsafe_result = scan_mql5_source_tree(tmp_path)
    unsafe_checks = {check.name: check for check in unsafe_result.safeguards}
    assert unsafe_result.status == "FAIL"
    assert unsafe_checks["TrialExecutionOrderGates"].status == "FAIL"


def test_python_mt5_order_execution_is_still_quarantined() -> None:
    matches = find_mt5_prohibited_patterns(
        ROOT,
        allowed_parts={"config", "data", "docs", "mql5", "tests", "tmp"},
        allowed_files={
            Path("src/trading_bot/audit/code_scan.py"),
            Path("src/trading_bot/mql5/source_scan.py"),
            Path("src/trading_bot/mt5/safety.py"),
        },
    )
    assert matches == []

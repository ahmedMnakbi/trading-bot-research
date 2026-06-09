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


def _input_value(name: str) -> str:
    match = re.search(rf"input\s+[\w_]+\s+{name}\s*=\s*([^;]+);", _ea_text())
    assert match, f"missing input {name}"
    return match.group(1).strip()


def test_phase13_defaults_keep_execution_disabled() -> None:
    assert _input_value("EnableTrading") == "false"
    assert _input_value("EnableTrialExecution") == "false"
    assert _input_value("EnablePropChallengeMode") == "false"
    assert _input_value("MaxTradesPerDay") == "1"
    assert _input_value("MaxOpenPositionsTotal") == "1"
    assert _input_value("MaxOpenPositionsPerSymbol") == "1"
    assert _input_value("AllowedSymbols") == '"EURUSD"'


def test_trial_execution_requires_exact_manual_confirmation() -> None:
    with pytest.raises(EaSettingsError, match="exact manual confirmation"):
        build_settings(
            overrides={
                "enable_trading": True,
                "enable_trial_execution": True,
                "manual_confirmation_text": "I ACCEPT MONITOR ONLY PHASE 5 - NO TRADING",
                "broker_time_validation_note": "broker server UTC offset manually verified",
            }
        )

    settings = build_settings(
        overrides={
            "enable_trading": True,
            "enable_trial_execution": True,
            "manual_confirmation_text": TRIAL_EXECUTION_MANUAL_CONFIRMATION,
            "broker_time_validation_note": "broker server UTC offset manually verified",
        },
        approval_metadata=ApprovalMetadata(source_scan_pass_id="scan-pass-1"),
    )
    assert settings.enable_trial_execution is True


def test_trial_execution_blocks_surge_vanguard_and_protected_stages() -> None:
    config_text = CONFIG.read_text(encoding="utf-8")
    assert "config.AccountProgram != ACCOUNT_PROGRAM_TRIAL_RISK_FREE" in config_text
    assert "config.AccountStage != ACCOUNT_STAGE_TRIAL" in config_text
    assert "Trial execution requires EnablePropChallengeMode=false" in config_text

    common = {
        "enable_trading": True,
        "enable_trial_execution": True,
        "manual_confirmation_text": TRIAL_EXECUTION_MANUAL_CONFIRMATION,
        "broker_time_validation_note": "broker server UTC offset manually verified",
    }
    with pytest.raises(EaSettingsError, match="TrialRiskFree"):
        build_settings(account_program="Surge2Step", overrides=common)
    with pytest.raises(EaSettingsError, match="TrialRiskFree"):
        build_settings(account_program="Vanguard", overrides=common)
    with pytest.raises(EaSettingsError, match="AccountStage Trial"):
        build_settings(stage="Challenge", overrides=common)


def test_order_calls_exist_only_in_isolated_execution_modules() -> None:
    tester_execution = INCLUDE_ROOT / "TesterExecution.mqh"
    assert "OrderSend(request, result)" in _trial_text()
    assert "OrderSend(request, result)" in tester_execution.read_text(encoding="utf-8")
    for path in MQL5_ROOT.rglob("*"):
        if path.suffix.lower() not in {".mq5", ".mqh"} or path in {
            TRIAL_EXECUTION,
            tester_execution,
        }:
            continue
        text = path.read_text(encoding="utf-8")
        assert "OrderSend" not in text
        assert "CTrade" not in text
        assert ".Buy(" not in text
        assert ".Sell(" not in text
        assert "PositionOpen" not in text


def test_trial_execution_module_has_required_gates_and_no_retry() -> None:
    text = _trial_text()
    required = [
        "ValidateTrialExecutionConfig",
        "ACCOUNT_PROGRAM_TRIAL_RISK_FREE",
        "ACCOUNT_STAGE_TRIAL",
        "HasTrialExecutionConfirmation",
        "SourceScanPassId",
        "StopLossRequired",
        "MinHoldSeconds",
        "MaxRiskPerTradePct",
        "RiskPerTradePct",
        "MaxOpenPositionsTotal",
        "MaxOpenPositionsPerSymbol",
        "MaxTradesPerDay",
        "MaxServerMessagesPerDay",
        "AllowedSymbols",
        "UseSpreadFilter",
        "MaxSpreadPoints",
        "HasStopLoss",
        "HasTakeProfit",
        "SYMBOL_TRADE_STOPS_LEVEL",
        "SYMBOL_POINT",
        "STOP_LEVEL_CONSTRAINT",
        "TRADE_ACTION_DEAL",
        "NO_RETRY_ORDER_SEND_ONCE",
        "NO_ACTION_SIGNAL_NOT_EXECUTABLE",
        "ARMED_TRIAL_EXECUTION_WAITING_FOR_VALID_SIGNAL",
        "RecordActualServerMessage",
    ]
    for snippet in required:
        assert snippet in text
    assert text.count("OrderSend(request, result)") == 1


def test_no_pending_order_or_retry_calls_exist() -> None:
    text = _trial_text()
    forbidden = [
        "ORDER_TYPE_BUY_LIMIT",
        "ORDER_TYPE_SELL_LIMIT",
        "ORDER_TYPE_BUY_STOP",
        "ORDER_TYPE_SELL_STOP",
        "BuyLimit",
        "SellLimit",
        "BuyStop",
        "SellStop",
        "while(",
        "for(;;",
    ]
    for snippet in forbidden:
        assert snippet not in text


def test_source_scanner_allows_only_isolated_trial_order_call() -> None:
    result = scan_mql5_source_tree(ROOT)
    checks = {check.name: check for check in result.safeguards}
    assert result.status == "PASS"
    assert checks["TrialExecutionOrderCallIsolation"].status == "PASS"
    assert checks["TrialExecutionOrderGates"].status == "PASS"


def test_source_scanner_fails_order_call_outside_trial_execution(tmp_path: Path) -> None:
    shutil.copytree(MQL5_ROOT, tmp_path / "mql5")
    unsafe = tmp_path / "mql5" / "Experts" / "Unsafe.mq5"
    unsafe.write_text("void OnTick() { OrderSend(request, result); }\n", encoding="utf-8")

    result = scan_mql5_source_tree(tmp_path)

    patterns = {violation["pattern"] for violation in result.violations}
    assert result.status == "FAIL"
    assert "mql5_order_send" in patterns


def test_source_scanner_fails_if_trial_order_gates_are_removed(tmp_path: Path) -> None:
    shutil.copytree(MQL5_ROOT, tmp_path / "mql5")
    trial_execution = (
        tmp_path / "mql5" / "Include" / "UpcomersNYSessionPropBot" / "TrialExecution.mqh"
    )
    trial_execution.write_text(
        trial_execution.read_text(encoding="utf-8").replace("SourceScanPassId", ""),
        encoding="utf-8",
    )

    result = scan_mql5_source_tree(tmp_path)
    checks = {check.name: check for check in result.safeguards}

    assert result.status == "FAIL"
    assert checks["TrialExecutionOrderGates"].status == "FAIL"


def test_python_mt5_order_execution_remains_quarantined() -> None:
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

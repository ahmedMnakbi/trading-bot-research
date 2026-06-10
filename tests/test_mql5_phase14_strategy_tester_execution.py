from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.parse_strategy_tester_report import parse_strategy_tester_report
from trading_bot.mql5.models import ApprovalMetadata
from trading_bot.mql5.settings import (
    APPROVED_STRATEGY_TESTER_SYMBOLS,
    STRATEGY_TESTER_ORB_PRESET,
    STRATEGY_TESTER_VWAP_PRESET,
    TRIAL_MICRO_EXECUTION_PRESET,
    EaSettingsError,
    build_settings,
    generate_settings_artifacts,
)
from trading_bot.mql5.source_scan import scan_mql5_source_tree

ROOT = Path(__file__).resolve().parents[1]
MQL5_ROOT = ROOT / "mql5"
EA_SOURCE = (
    MQL5_ROOT
    / "Experts"
    / "UpcomersNYSessionPropBot"
    / "UpcomersNYSessionPropBot.mq5"
)
INCLUDE_ROOT = MQL5_ROOT / "Include" / "UpcomersNYSessionPropBot"
CONFIG = INCLUDE_ROOT / "Config.mqh"
TRIAL_EXECUTION = INCLUDE_ROOT / "TrialExecution.mqh"
TESTER_EXECUTION = INCLUDE_ROOT / "TesterExecution.mqh"


def _ea_text() -> str:
    return EA_SOURCE.read_text(encoding="utf-8")


def _tester_text() -> str:
    return TESTER_EXECUTION.read_text(encoding="utf-8")


def _input_value(name: str) -> str:
    match = re.search(rf"input\s+[\w_]+\s+{name}\s*=\s*([^;]+);", _ea_text())
    assert match, f"missing input {name}"
    return match.group(1).strip()


def test_strategy_tester_mode_disabled_by_default() -> None:
    assert _input_value("EnableTrading") == "false"
    assert _input_value("EnableTrialExecution") == "false"
    assert _input_value("StrategyTesterExecutionMode") == "false"
    assert _input_value("EnablePropChallengeMode") == "false"


def test_strategy_tester_execution_cannot_activate_outside_tester() -> None:
    ea_text = _ea_text()
    config_text = CONFIG.read_text(encoding="utf-8")

    assert "MQLInfoInteger(MQL_TESTER)" in ea_text
    assert "GATE_FAIL_%s" in ea_text
    assert "TESTER_RUNTIME" in ea_text
    assert "StrategyTesterExecutionMode requires MQL_TESTER runtime" in config_text
    assert "ValidateRuntimeExecutionConfig(g_config, isStrategyTesterRuntime, reason)" in (
        ea_text
    )


def test_live_trial_execution_gates_remain_unchanged() -> None:
    config_text = CONFIG.read_text(encoding="utf-8")
    trial_text = TRIAL_EXECUTION.read_text(encoding="utf-8")
    settings = build_settings(
        preset_name=TRIAL_MICRO_EXECUTION_PRESET,
        approval_metadata=ApprovalMetadata(source_scan_pass_id="scan-pass"),
        overrides={
            "broker_time_validation_note": "broker server UTC offset manually verified",
        },
    )

    assert settings.enable_trial_execution is True
    assert settings.strategy_tester_execution_mode is False
    assert "Trial execution requires AccountProgram=TrialRiskFree" in config_text
    assert "Trial execution requires AccountStage=Trial" in config_text
    assert "Trial execution requires AllowedSymbols=EURUSD only" in config_text
    assert "I_ACCEPT_TRIAL_RISK_FREE_EXECUTION_ONLY" in config_text
    assert "OrderSend(request, result)" in trial_text
    assert trial_text.count("OrderSend(request, result)") == 1


def test_strategy_tester_symbol_gate_uses_strict_research_allowlist() -> None:
    config_text = CONFIG.read_text(encoding="utf-8")
    ea_text = _ea_text()

    assert "IsStrategyTesterResearchSymbolAllowed" in config_text
    assert 'allowedSymbols == "EURUSD"' in config_text
    assert 'allowedSymbols == "NACUSD.c"' in config_text
    assert 'allowedSymbols == "SPCUSD.c"' in config_text
    assert "AllowedSymbols to be one approved research tester symbol" in config_text
    assert "EURUSD, NACUSD.c, or SPCUSD.c" in config_text
    assert "TESTER_ALLOWED_SYMBOLS" in ea_text
    assert "EURUSD|NACUSD.c|SPCUSD.c" in ea_text


@pytest.mark.parametrize("symbol", ["EURUSD", "NACUSD.c", "SPCUSD.c"])
def test_python_strategy_tester_validation_accepts_approved_symbols(symbol: str) -> None:
    settings = build_settings(
        stage="MonitorOnly",
        overrides={
            "strategy_tester_execution_mode": True,
            "allowed_symbols": symbol,
            "strategy_timeframe": "PERIOD_M5",
        },
    )

    assert settings.strategy_tester_execution_mode is True
    assert settings.allowed_symbols == symbol
    assert symbol in APPROVED_STRATEGY_TESTER_SYMBOLS


def test_python_strategy_tester_validation_rejects_unapproved_symbol() -> None:
    with pytest.raises(EaSettingsError, match="approved research tester symbol"):
        build_settings(
            stage="MonitorOnly",
            overrides={
                "strategy_tester_execution_mode": True,
                "allowed_symbols": "XAUUSD",
                "strategy_timeframe": "PERIOD_M5",
            },
        )


def test_python_strategy_tester_validation_still_requires_disabled_execution_flags() -> None:
    with pytest.raises(EaSettingsError, match="EnableTrading=false"):
        build_settings(
            stage="MonitorOnly",
            overrides={
                "strategy_tester_execution_mode": True,
                "enable_trading": True,
                "allowed_symbols": "NACUSD.c",
                "strategy_timeframe": "PERIOD_M5",
            },
        )
    with pytest.raises(EaSettingsError, match="separate from EnableTrialExecution"):
        build_settings(
            stage="MonitorOnly",
            overrides={
                "strategy_tester_execution_mode": True,
                "enable_trial_execution": True,
                "allowed_symbols": "NACUSD.c",
                "strategy_timeframe": "PERIOD_M5",
            },
        )


def test_python_trial_validation_still_rejects_index_symbols() -> None:
    with pytest.raises(EaSettingsError, match="AllowedSymbols=EURUSD"):
        build_settings(
            preset_name=TRIAL_MICRO_EXECUTION_PRESET,
            approval_metadata=ApprovalMetadata(source_scan_pass_id="scan-pass"),
            overrides={
                "allowed_symbols": "NACUSD.c",
                "broker_time_validation_note": "broker server UTC offset manually verified",
            },
        )


def test_tester_execution_order_call_is_isolated() -> None:
    assert "OrderSend(request, result)" in TRIAL_EXECUTION.read_text(encoding="utf-8")
    assert "OrderSend(request, result)" in _tester_text()
    assert _tester_text().count("OrderSend(request, result)") == 1

    for path in MQL5_ROOT.rglob("*"):
        if path.suffix.lower() not in {".mq5", ".mqh"} or path in {
            TRIAL_EXECUTION,
            TESTER_EXECUTION,
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


def test_tester_execution_non_entry_signals_cannot_execute() -> None:
    text = _tester_text()
    non_entry_section = text.split("if(!LogGate(logger, \"MQL_TESTER\"")[0]

    assert "decision.Signal != SIGNAL_ENTER_LONG_INTENT" in non_entry_section
    assert "decision.Signal != SIGNAL_ENTER_SHORT_INTENT" in non_entry_section
    assert "TESTER_NO_ACTION_SIGNAL_NOT_EXECUTABLE" in non_entry_section
    assert "OrderSend" not in non_entry_section


def test_strategy_tester_presets_generate_orb_and_vwap_settings(tmp_path: Path) -> None:
    for preset, strategy in [
        (STRATEGY_TESTER_ORB_PRESET, "STRATEGY_OPENING_RANGE_BREAKOUT"),
        (STRATEGY_TESTER_VWAP_PRESET, "STRATEGY_VWAP_TREND_CONTINUATION"),
    ]:
        output = tmp_path / f"{preset}.set"
        result = generate_settings_artifacts(
            output_path=output,
            preset_name=preset,
            stage="MonitorOnly",
        )
        text = output.read_text(encoding="utf-8")
        summary = json.loads(Path(result.summary_json_path).read_text(encoding="utf-8"))

        assert result.status == "PASS"
        assert "EnableTrading=false" in text
        assert "EnableTrialExecution=false" in text
        assert "StrategyTesterExecutionMode=true" in text
        assert "EnablePropChallengeMode=false" in text
        assert "AccountProgram=ACCOUNT_PROGRAM_TRIAL_RISK_FREE" in text
        assert "AccountStage=ACCOUNT_STAGE_MONITOR_ONLY" in text
        assert "AllowedSymbols=EURUSD" in text
        assert "StrategyTimeframe=PERIOD_M5" in text
        assert f"StrategySelection={strategy}" in text
        assert summary["strategy_tester_execution_mode"] is True
        assert summary["strategy_tester_preset"] is True


@pytest.mark.parametrize("program", ["Surge2Step", "Vanguard", "Custom"])
def test_strategy_tester_presets_block_surge_vanguard_and_custom(program: str) -> None:
    with pytest.raises(EaSettingsError, match="TrialRiskFree|rules are unverified|Vanguard"):
        build_settings(
            preset_name=STRATEGY_TESTER_ORB_PRESET,
            account_program=program,
            stage="MonitorOnly",
        )


@pytest.mark.parametrize("stage", ["Trial", "Challenge", "Verification", "Funded"])
def test_strategy_tester_presets_block_non_monitor_stages(stage: str) -> None:
    with pytest.raises(EaSettingsError, match="MonitorOnly|protected stage"):
        build_settings(
            preset_name=STRATEGY_TESTER_ORB_PRESET,
            stage=stage,
        )


def test_strategy_tester_parser_summarizes_simulated_backtest(tmp_path: Path) -> None:
    report = tmp_path / "tester.html"
    report.write_text(
        "\n".join(
            [
                "Strategy Tester Report",
                "Symbol: EURUSD",
                "Timeframe: M5",
                "Model: Every tick based on real ticks",
                "StrategyTesterExecutionMode=true",
                "EnableTrading=false",
                "EnableTrialExecution=false",
                "EnablePropChallengeMode=false",
                "Total trades: 3",
                "Orders: 3",
                "Deals: 6",
                "Profit Factor: 1.42",
                "Maximal drawdown: 2.1%",
                "Expected Payoff: 4.25",
                "Average hold time: 00:07:30",
                "trade closed hold=00:03:05",
            ]
        ),
        encoding="utf-8",
    )

    result = parse_strategy_tester_report(report, monitor_only=False)

    assert result.status == "PASS"
    assert result.activity_counts == {"trades": 3, "orders": 3, "deals": 6}
    assert result.performance_metrics["number_of_trades"] == 3
    assert result.performance_metrics["profit_factor"] == "1.42"
    assert result.performance_metrics["drawdown"] == "2.1%"
    assert result.performance_metrics["expected_payoff"] == "4.25"
    assert result.performance_metrics["average_hold_time"] == "00:07:30"
    assert result.sub_180_second_closes == []


def test_strategy_tester_parser_flags_sub_180_second_closes(tmp_path: Path) -> None:
    report = tmp_path / "tester.html"
    report.write_text(
        "\n".join(
            [
                "Strategy Tester Report",
                "EnableTrading=false",
                "EnableTrialExecution=false",
                "EnablePropChallengeMode=false",
                "Total trades: 1",
                "Orders: 1",
                "Deals: 2",
                "Profit Factor: 0.90",
                "trade closed hold=00:02:59",
            ]
        ),
        encoding="utf-8",
    )

    result = parse_strategy_tester_report(report, monitor_only=False)

    assert result.status == "FAIL"
    assert "sub_180_second_closes_detected" in result.warnings
    assert result.sub_180_second_closes


def test_source_scan_accepts_only_isolated_tester_execution() -> None:
    result = scan_mql5_source_tree(ROOT)
    checks = {check.name: check for check in result.safeguards}

    assert result.status == "PASS"
    assert checks["TrialExecutionOrderCallIsolation"].status == "PASS"
    assert checks["TesterExecutionOrderGates"].status == "PASS"
    assert checks["strategy_tester_execution_runtime_gate"].status == "PASS"

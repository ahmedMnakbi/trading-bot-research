from __future__ import annotations

from pathlib import Path

from scripts import generate_ea_settings
from scripts.parse_strategy_tester_report import parse_strategy_tester_report
from trading_bot.mql5.settings import (
    STRATEGY_TESTER_ORB_PRESET,
    STRATEGY_TESTER_VWAP_PRESET,
)

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
TESTER_EXECUTION = INCLUDE_ROOT / "TesterExecution.mqh"
STRATEGY_DIAGNOSTICS = INCLUDE_ROOT / "StrategyDiagnostics.mqh"


def _set_value(text: str, name: str) -> str:
    prefix = f"{name}="
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix)
    raise AssertionError(f"missing {name}")


def test_orb_and_vwap_cli_presets_select_expected_strategy(tmp_path: Path) -> None:
    cases = [
        (STRATEGY_TESTER_ORB_PRESET, "STRATEGY_OPENING_RANGE_BREAKOUT"),
        (STRATEGY_TESTER_VWAP_PRESET, "STRATEGY_VWAP_TREND_CONTINUATION"),
    ]
    for preset, expected_strategy in cases:
        output = tmp_path / f"{preset}.set"
        code = generate_ea_settings.main(
            [
                "--preset",
                preset,
                "--output-path",
                str(output),
                "--json",
            ]
        )

        text = output.read_text(encoding="utf-8")

        assert code == 0
        assert _set_value(text, "StrategySelection") == expected_strategy
        assert _set_value(text, "StrategyTesterExecutionMode") == "true"
        assert _set_value(text, "EnableTrading") == "false"
        assert _set_value(text, "EnableTrialExecution") == "false"
        assert _set_value(text, "EnablePropChallengeMode") == "false"
        assert _set_value(text, "AllowedSymbols") == "EURUSD"
        assert _set_value(text, "StrategyTimeframe") == "PERIOD_M5"
        assert _set_value(text, "BrokerServerUtcOffsetMinutes") == "120"


def test_strategy_tester_diagnostics_markers_are_logged_on_tester_end() -> None:
    ea_text = EA_SOURCE.read_text(encoding="utf-8")
    diagnostics_text = STRATEGY_DIAGNOSTICS.read_text(encoding="utf-8")
    diagnostics_include = (
        "#include \"..\\\\..\\\\Include\\\\UpcomersNYSessionPropBot\\\\"
        "StrategyDiagnostics.mqh\""
    )

    assert diagnostics_include in ea_text
    assert "g_strategyDiagnostics.RecordDecision(decision)" in ea_text
    assert "RecordTesterOrderAttempt()" in ea_text
    assert "double OnTester()" in ea_text
    assert "LogStrategyDiagnosticsSummary(\"OnDeinit\")" in ea_text
    assert "STRATEGY_DIAGNOSTICS_SUMMARY" in diagnostics_text
    for token in [
        "WAIT",
        "SETUP_FORMING",
        "SKIP_SESSION",
        "SPREAD_BLOCK",
        "ORB_WIDTH_BLOCK",
        "RETEST_FAIL",
        "ORB_SIGNAL_COOLDOWN",
        "ENTER_LONG_INTENT",
        "ENTER_SHORT_INTENT",
        "VWAP_BIAS_LONG",
        "VWAP_BIAS_SHORT",
        "VWAP_FLAT_BLOCK",
        "IMPULSE_MISSING",
        "PULLBACK_NEAR_VWAP",
        "REJECTION_CLOSE_OK",
    ]:
        assert token in diagnostics_text


def test_strategy_tester_parser_extracts_diagnostics_summary(tmp_path: Path) -> None:
    report = tmp_path / "strategy_tester_eurusd_m5_orb.log"
    report.write_text(
        "\n".join(
            [
                "Preset=strategy-tester-eurusd-m5-orb",
                "StrategySelection=STRATEGY_OPENING_RANGE_BREAKOUT",
                "StrategyTesterExecutionMode=true",
                "EnableTrading=false",
                "EnableTrialExecution=false",
                "EnablePropChallengeMode=false",
                "Total trades: 0",
                "Orders: 0",
                "Deals: 0",
                (
                    "STRATEGY_DIAGNOSTICS_SUMMARY "
                    "strategy=STRATEGY_OPENING_RANGE_BREAKOUT "
                    "total_evaluations=42 enter_long=0 enter_short=0 "
                    "tester_execution_mode=true tester_runtime=true "
                    "tester_orders_attempted=0 "
                    "top_reason_codes=WAIT:3|SETUP_FORMING:12|ORB_WIDTH_BLOCK:8"
                ),
            ]
        ),
        encoding="utf-8",
    )

    result = parse_strategy_tester_report(report, monitor_only=False)

    assert result.status == "PASS"
    assert result.strategy_diagnostics["strategy"] == "STRATEGY_OPENING_RANGE_BREAKOUT"
    assert result.strategy_diagnostics["total_evaluations"] == 42
    assert result.strategy_diagnostics["enter_long"] == 0
    assert result.strategy_diagnostics["enter_short"] == 0
    assert result.strategy_diagnostics["reason_counts"]["ORB_WIDTH_BLOCK"] == 8
    assert result.diagnostics_assessment == "no executable entry signals generated"
    assert "no executable entry signals generated" in result.message


def test_strategy_tester_parser_reports_execution_gate_blocked_entries(
    tmp_path: Path,
) -> None:
    report = tmp_path / "strategy_tester_eurusd_m5_orb.log"
    report.write_text(
        "\n".join(
            [
                "StrategyTesterExecutionMode=true",
                "EnableTrading=false",
                "EnableTrialExecution=false",
                "EnablePropChallengeMode=false",
                "Total trades: 0",
                "Orders: 0",
                "Deals: 0",
                (
                    "STRATEGY_DIAGNOSTICS_SUMMARY "
                    "strategy=STRATEGY_OPENING_RANGE_BREAKOUT "
                    "total_evaluations=7 enter_long=2 enter_short=0 "
                    "tester_execution_mode=true tester_runtime=true "
                    "tester_orders_attempted=0 "
                    "top_reason_codes=ENTER_LONG_INTENT:2|WAIT:5"
                ),
            ]
        ),
        encoding="utf-8",
    )

    result = parse_strategy_tester_report(report, monitor_only=False)

    assert result.status == "PASS"
    assert result.diagnostics_assessment == "execution gate blocked entries"
    assert "execution gate blocked entries" in result.message


def test_strategy_tester_parser_flags_vwap_preset_selecting_orb(tmp_path: Path) -> None:
    report = tmp_path / "strategy_tester_eurusd_m5_vwap.log"
    report.write_text(
        "\n".join(
            [
                "Preset=strategy-tester-eurusd-m5-vwap",
                "StrategySelection=STRATEGY_OPENING_RANGE_BREAKOUT",
                "StrategyTesterExecutionMode=true",
                "EnableTrading=false",
                "EnableTrialExecution=false",
                "EnablePropChallengeMode=false",
                "Total trades: 0",
                "Orders: 0",
                "Deals: 0",
            ]
        ),
        encoding="utf-8",
    )

    result = parse_strategy_tester_report(report, monitor_only=False)

    assert result.status == "FAIL"
    assert "vwap_preset_selects_orb" in result.warnings


def test_no_new_order_calls_outside_trial_and_tester_execution() -> None:
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

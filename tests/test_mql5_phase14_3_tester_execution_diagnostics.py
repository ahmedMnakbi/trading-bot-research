from __future__ import annotations

import json
from pathlib import Path

from scripts.inspect_ea_settings import inspect_settings_file
from scripts.parse_strategy_tester_report import parse_strategy_tester_report

ROOT = Path(__file__).resolve().parents[1]
MQL5_ROOT = ROOT / "mql5"
INCLUDE_ROOT = MQL5_ROOT / "Include" / "UpcomersNYSessionPropBot"
CONFIG = INCLUDE_ROOT / "Config.mqh"
TESTER_EXECUTION = INCLUDE_ROOT / "TesterExecution.mqh"
TRIAL_EXECUTION = INCLUDE_ROOT / "TrialExecution.mqh"


def _tester_text() -> str:
    return TESTER_EXECUTION.read_text(encoding="utf-8")


def test_tester_execution_logs_entry_gate_request_and_summary_markers() -> None:
    text = _tester_text()

    for token in [
        "TESTER_ENTRY_INTENT_RECEIVED",
        "TESTER_GATE_FAIL_%s",
        "TESTER_ORDER_REQUEST",
        "TESTER_EXECUTION_SUMMARY",
        "tester_entry_intents_received=%d",
        "tester_orders_attempted=%d",
        "tester_orders_sent_success=%d",
        "tester_orders_rejected=%d",
        "tester_orders_skipped_by_gate=%d",
        "top_tester_gate_failures=%s",
        "ValidateStrategyTesterExecutionConfig",
        "Spread",
        "SLTP",
        "LotSize",
    ]:
        assert token in text


def test_strategy_tester_simulated_execution_keeps_live_trial_toggles_off() -> None:
    config_text = CONFIG.read_text(encoding="utf-8")
    tester_text = _tester_text()

    assert "StrategyTesterExecutionMode requires EnableTrading=false on inputs" in config_text
    assert "StrategyTesterExecutionMode is separate from EnableTrialExecution" in config_text
    assert "EnableTradingInputFalse" in tester_text
    assert "!config.EnableTrading" in tester_text
    assert "EnableTrialExecutionFalse" in tester_text
    assert "!config.EnableTrialExecution" in tester_text


def test_tester_runtime_gate_still_prevents_live_chart_activation() -> None:
    config_text = CONFIG.read_text(encoding="utf-8")
    tester_text = _tester_text()

    assert "StrategyTesterExecutionMode requires MQL_TESTER runtime" in config_text
    assert "MQL_TESTER" in tester_text
    assert "isStrategyTesterRuntime" in tester_text


def test_parser_extracts_tester_execution_gate_summary(tmp_path: Path) -> None:
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
                    "total_evaluations=5988 enter_long=9 enter_short=12 "
                    "tester_execution_mode=true tester_runtime=true "
                    "tester_orders_attempted=0 top_reason_codes=ENTER_LONG_INTENT:9"
                ),
                (
                    "TESTER_GATE_FAIL_Spread "
                    "detail=spread=41 max=30"
                ),
                (
                    "TESTER_EXECUTION_SUMMARY "
                    "tester_entry_intents_received=21 "
                    "tester_orders_attempted=0 "
                    "tester_orders_sent_success=0 "
                    "tester_orders_rejected=0 "
                    "tester_orders_skipped_by_gate=21 "
                    "top_tester_gate_failures=Spread:21|LotSize:0 "
                    "last_tester_gate_failure=Spread event=OnTester"
                ),
            ]
        ),
        encoding="utf-8",
    )

    result = parse_strategy_tester_report(report, monitor_only=False)

    assert result.status == "PASS"
    assert result.diagnostics_assessment == "entry intents did not reach tester order request"
    assert result.tester_execution_summary["tester_entry_intents_received"] == 21
    assert result.tester_execution_summary["tester_orders_attempted"] == 0
    assert result.tester_execution_summary["gate_failure_counts"]["Spread"] == 21
    assert result.tester_execution_summary["gate_failure_details"] == [
        "Spread: spread=41 max=30"
    ]
    assert "Spread=21" in result.message


def test_parser_reports_attempted_orders_with_zero_reported_trades(
    tmp_path: Path,
) -> None:
    report = tmp_path / "strategy_tester_eurusd_m5_vwap.log"
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
                    "strategy=STRATEGY_VWAP_TREND_CONTINUATION "
                    "total_evaluations=12269 enter_long=21 enter_short=19 "
                    "tester_execution_mode=true tester_runtime=true "
                    "tester_orders_attempted=2 top_reason_codes=ENTER_LONG_INTENT:21"
                ),
                (
                    "TESTER_EXECUTION_BROKER_RESPONSE simulated=true sent=false "
                    "retcode=10030 order=0 deal=0 comment=invalid stops no_retry=true"
                ),
                (
                    "TESTER_EXECUTION_SUMMARY "
                    "tester_entry_intents_received=40 "
                    "tester_orders_attempted=2 "
                    "tester_orders_sent_success=0 "
                    "tester_orders_rejected=2 "
                    "tester_orders_skipped_by_gate=38 "
                    "top_tester_gate_failures=SLTP:38 "
                    "last_tester_gate_failure=SLTP event=OnTester"
                ),
            ]
        ),
        encoding="utf-8",
    )

    result = parse_strategy_tester_report(report, monitor_only=False)

    assert result.status == "PASS"
    assert result.diagnostics_assessment == "tester orders attempted but report shows zero trades"
    assert result.tester_execution_summary["tester_orders_attempted"] == 2
    assert result.tester_execution_summary["tester_orders_rejected"] == 2
    assert result.tester_execution_summary["rejection_details"]


def test_inspect_ea_settings_detects_vwap_file_selecting_orb(tmp_path: Path) -> None:
    set_path = tmp_path / "strategy_tester_eurusd_m5_vwap.set"
    set_path.write_text(
        "\n".join(
            [
                "EnableTrading=false",
                "EnableTrialExecution=false",
                "StrategyTesterExecutionMode=true",
                "EnablePropChallengeMode=false",
                "AccountStage=ACCOUNT_STAGE_MONITOR_ONLY",
                "AllowedSymbols=EURUSD",
                "StrategySelection=STRATEGY_OPENING_RANGE_BREAKOUT",
            ]
        ),
        encoding="utf-8",
    )
    set_path.with_suffix(".summary.json").write_text(
        json.dumps({"preset_name": "strategy-tester-eurusd-m5-vwap"}),
        encoding="utf-8",
    )

    result = inspect_settings_file(set_path)

    assert result["status"] == "FAIL"
    assert "vwap_preset_selects_orb" in result["failures"]


def test_inspect_ea_settings_accepts_safe_vwap_tester_preset(tmp_path: Path) -> None:
    set_path = tmp_path / "strategy_tester_eurusd_m5_vwap.set"
    set_path.write_text(
        "\n".join(
            [
                "EnableTrading=false",
                "EnableTrialExecution=false",
                "StrategyTesterExecutionMode=true",
                "EnablePropChallengeMode=false",
                "AccountStage=ACCOUNT_STAGE_MONITOR_ONLY",
                "AllowedSymbols=EURUSD",
                "StrategySelection=STRATEGY_VWAP_TREND_CONTINUATION",
                "StrategyTimeframe=PERIOD_M5",
            ]
        ),
        encoding="utf-8",
    )
    set_path.with_suffix(".summary.json").write_text(
        json.dumps({"preset_name": "strategy-tester-eurusd-m5-vwap"}),
        encoding="utf-8",
    )

    result = inspect_settings_file(set_path)

    assert result["status"] == "PASS"
    assert result["settings"]["StrategySelection"] == "STRATEGY_VWAP_TREND_CONTINUATION"


def test_inspect_ea_settings_accepts_nacusd_research_tester_preset(
    tmp_path: Path,
) -> None:
    set_path = tmp_path / (
        "strategy_tester_nacusd_c_m5_ny_m15_sweep_reclaim_relaxed_m15_direction.set"
    )
    set_path.write_text(
        "\n".join(
            [
                "EnableTrading=false",
                "EnableTrialExecution=false",
                "StrategyTesterExecutionMode=true",
                "EnablePropChallengeMode=false",
                "AccountStage=ACCOUNT_STAGE_MONITOR_ONLY",
                "AllowedSymbols=NACUSD.c",
                "StrategySelection=STRATEGY_NY_M15_SWEEP_RECLAIM",
                "StrategyTimeframe=PERIOD_M5",
                "NYM15SRRequireM15DirectionAgreement=false",
            ]
        ),
        encoding="utf-8",
    )
    set_path.with_suffix(".summary.json").write_text(
        json.dumps(
            {
                "preset_name": (
                    "strategy-tester-nacusd-c-m5-ny-m15-sweep-reclaim-"
                    "relaxed-m15-direction"
                )
            }
        ),
        encoding="utf-8",
    )

    result = inspect_settings_file(set_path)

    assert result["status"] == "PASS"
    assert result["settings"]["AllowedSymbols"] == "NACUSD.c"


def test_inspect_ea_settings_rejects_unapproved_tester_symbol(
    tmp_path: Path,
) -> None:
    set_path = tmp_path / "strategy_tester_xauusd_m5.set"
    set_path.write_text(
        "\n".join(
            [
                "EnableTrading=false",
                "EnableTrialExecution=false",
                "StrategyTesterExecutionMode=true",
                "EnablePropChallengeMode=false",
                "AccountStage=ACCOUNT_STAGE_MONITOR_ONLY",
                "AllowedSymbols=XAUUSD",
                "StrategySelection=STRATEGY_NY_M15_SWEEP_RECLAIM",
            ]
        ),
        encoding="utf-8",
    )

    result = inspect_settings_file(set_path)

    assert result["status"] == "FAIL"
    assert "strategy_tester_requires_approved_research_symbol" in result["failures"]


def test_no_new_order_call_locations_for_phase14_3() -> None:
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

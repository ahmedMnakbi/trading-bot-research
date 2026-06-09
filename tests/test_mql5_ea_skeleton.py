from __future__ import annotations

import re
from pathlib import Path

from scripts.run_mql5_source_scan import run_mql5_source_scan

ROOT = Path(__file__).resolve().parents[1]
MQL5_ROOT = ROOT / "mql5"
EA_SOURCE = (
    MQL5_ROOT
    / "Experts"
    / "UpcomersNYSessionPropBot"
    / "UpcomersNYSessionPropBot.mq5"
)
INCLUDE_ROOT = MQL5_ROOT / "Include" / "UpcomersNYSessionPropBot"

REQUIRED_MODULES = [
    "Config.mqh",
    "Logger.mqh",
    "RiskManager.mqh",
    "PropFirmRules.mqh",
    "SessionManager.mqh",
    "SymbolManager.mqh",
    "StrategyBase.mqh",
    "StrategyDiagnostics.mqh",
    "OpeningRangeBreakout.mqh",
    "VWAPTrendContinuation.mqh",
    "NoiseBandMomentum.mqh",
    "LondonNYOverlapMomentum.mqh",
    "VolatilityExpansion.mqh",
    "TradeManager.mqh",
    "TrialExecution.mqh",
    "TesterExecution.mqh",
    "StateManager.mqh",
    "AuditLogger.mqh",
    "MessageCounter.mqh",
    "NewsFilterPlaceholder.mqh",
]


def _source_text() -> str:
    return EA_SOURCE.read_text(encoding="utf-8")


def _all_mql5_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in MQL5_ROOT.rglob("*.mq*"))


def _input_value(name: str) -> str:
    match = re.search(rf"input\s+\w+(?:_\w+)*\s+{name}\s*=\s*([^;]+);", _source_text())
    assert match, f"missing input {name}"
    return match.group(1).strip()


def test_ea_source_and_required_modules_exist() -> None:
    assert EA_SOURCE.exists()
    for module in REQUIRED_MODULES:
        assert (INCLUDE_ROOT / module).exists(), f"missing {module}"


def test_phase4_safe_inputs_are_disabled_by_default() -> None:
    assert _input_value("EnableTrading") == "false"
    assert _input_value("EnableTrialExecution") == "false"
    assert _input_value("StrategyTesterExecutionMode") == "false"
    assert _input_value("EnablePropChallengeMode") == "false"
    assert _input_value("AccountProgram") == "ACCOUNT_PROGRAM_TRIAL_RISK_FREE"
    assert _input_value("AccountStage") == "ACCOUNT_STAGE_MONITOR_ONLY"
    assert _input_value("RequireManualConfirmationText") == "true"
    assert _input_value("StopLossRequired") == "true"
    assert _input_value("AllowedSymbols") == '"EURUSD"'
    assert _input_value("MaxTradesPerDay") == "1"
    assert _input_value("MaxOpenPositionsTotal") == "1"
    assert _input_value("AllowGrid") == "false"
    assert _input_value("AllowMartingale") == "false"
    assert _input_value("AllowAveragingDown") == "false"
    assert _input_value("AllowHFT") == "false"
    assert _input_value("AllowScalpingUnder2Minutes") == "false"


def test_minimum_hold_and_loss_limits_are_stricter_than_upcomers_caps() -> None:
    assert int(_input_value("MinHoldSeconds")) >= 180
    assert float(_input_value("MaxDailyLossSoftPct")) == 2.5
    assert float(_input_value("MaxDailyLossHardPct")) == 3.0
    assert float(_input_value("MaxOverallLossSoftPct")) == 5.0
    assert float(_input_value("MaxOverallLossHardPct")) == 6.0
    assert float(_input_value("MaxDailyLossHardPct")) < 4.0
    assert float(_input_value("MaxOverallLossHardPct")) < 7.0


def test_phase4_event_handlers_and_monitor_only_logs_exist() -> None:
    text = _source_text()

    assert "int OnInit()" in text
    assert "void OnDeinit" in text
    assert "void OnTick()" in text
    assert "void OnTimer()" in text
    assert "Monitor-only mode is active" in text
    assert "not approved for Surge 2 Step, Vanguard, Challenge, Verification, Funded" in text


def test_order_placement_calls_are_isolated_to_execution_modules() -> None:
    text = _all_mql5_text()
    assert "OrderSend" in text
    trial_execution_text = (INCLUDE_ROOT / "TrialExecution.mqh").read_text(encoding="utf-8")
    tester_execution_text = (INCLUDE_ROOT / "TesterExecution.mqh").read_text(encoding="utf-8")
    assert "OrderSend(request, result)" in trial_execution_text
    assert "OrderSend(request, result)" in tester_execution_text
    for path in MQL5_ROOT.rglob("*"):
        if path.suffix.lower() not in {".mq5", ".mqh"}:
            continue
        path_text = path.read_text(encoding="utf-8")
        if path.name in {"TrialExecution.mqh", "TesterExecution.mqh"}:
            continue
        for pattern in [
            "OrderSend",
            ".Buy(",
            ".Sell(",
            "PositionOpen",
            "BuyLimit",
            "SellLimit",
            "BuyStop",
            "SellStop",
        ]:
            assert pattern not in path_text


def test_trade_manager_is_no_trade_stub() -> None:
    text = (INCLUDE_ROOT / "TradeManager.mqh").read_text(encoding="utf-8")

    assert "RefuseExecution" in text
    assert "return false" in text
    assert "Phase 9 no-trade" in text


def test_phase6_strategy_modules_are_signal_only() -> None:
    strategy_text = "\n".join(
        (INCLUDE_ROOT / name).read_text(encoding="utf-8")
        for name in [
            "OpeningRangeBreakout.mqh",
            "VWAPTrendContinuation.mqh",
            "NoiseBandMomentum.mqh",
            "LondonNYOverlapMomentum.mqh",
            "VolatilityExpansion.mqh",
        ]
    )

    assert "SetWaitDecision" in strategy_text
    assert "SetSetupFormingDecision" in strategy_text
    assert "SetEntryIntentDecision" in strategy_text
    assert "monitor-only" in strategy_text
    assert "OrderSend" not in strategy_text


def test_mql5_source_scan_passes_current_phase4_source() -> None:
    result = run_mql5_source_scan(ROOT)

    assert result.status == "PASS"
    assert result.violations == []

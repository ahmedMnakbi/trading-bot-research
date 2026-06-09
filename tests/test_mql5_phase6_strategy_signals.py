from __future__ import annotations

from pathlib import Path

from scripts.compile_mql5_ea import compile_ea
from scripts.run_mql5_source_scan import run_mql5_source_scan

ROOT = Path(__file__).resolve().parents[1]
MQL5_ROOT = ROOT / "mql5"
INCLUDE_ROOT = MQL5_ROOT / "Include" / "UpcomersNYSessionPropBot"
EA_SOURCE = (
    MQL5_ROOT
    / "Experts"
    / "UpcomersNYSessionPropBot"
    / "UpcomersNYSessionPropBot.mq5"
)


def _read(name: str) -> str:
    return (INCLUDE_ROOT / name).read_text(encoding="utf-8")


def _all_mql5_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in MQL5_ROOT.rglob("*.mq*"))


def test_strategy_interface_includes_phase6_signal_types_and_fields() -> None:
    text = _read("StrategyBase.mqh")

    for signal in [
        "SIGNAL_WAIT",
        "SIGNAL_SETUP_FORMING",
        "SIGNAL_ENTER_LONG_INTENT",
        "SIGNAL_ENTER_SHORT_INTENT",
        "SIGNAL_EXIT_INTENT",
        "SIGNAL_SKIP_SESSION",
        "SIGNAL_SKIP_SPREAD",
        "SIGNAL_SKIP_NEWS",
        "SIGNAL_SKIP_DATA",
        "SIGNAL_SESSION_CLOSE",
    ]:
        assert signal in text

    for field in [
        "StrategyName",
        "SymbolName",
        "SymbolClass",
        "Timeframe",
        "Direction",
        "ReasonCode",
        "ReasonCodes",
        "Timestamp",
        "ServerTimestamp",
        "NewYorkTimestamp",
        "SessionTag",
        "SuggestedEntry",
        "SuggestedStopLoss",
        "SuggestedTakeProfit",
        "MinHoldUntil",
        "SpreadFilterStatus",
        "VolumeTypeUsed",
        "MonitorOnlyNote",
        "QualityScore",
        "HasSuggestedEntry",
        "HasStopLoss",
    ]:
        assert field in text


def test_entry_intents_require_stop_loss_in_strategy_interface() -> None:
    text = _read("StrategyBase.mqh")

    assert "SetEntryIntentDecision" in text
    assert "stopLoss <= 0.0" in text
    assert "SIGNAL_SKIP_DATA" in text
    assert "EntryIntentHasRequiredStopLoss" in text


def test_opening_range_breakout_has_session_gate_and_completion_logic() -> None:
    text = _read("OpeningRangeBreakout.mqh")

    assert "IsEntrySessionForSymbol" in text
    assert "SIGNAL_SKIP_SESSION" in text
    assert "closed M1 bars from session start" in text
    assert "openingRangeMinutes" in text
    assert "OpeningRangeMinutesToM1Bars" in text
    assert "PERIOD_M1" in text
    assert "CopyRates" in text
    assert "rangeHigh" in text
    assert "rangeLow" in text
    assert "ORB_TINY_RANGE" in text


def test_opening_range_breakout_requires_stop_loss_and_avoids_repeats() -> None:
    text = _read("OpeningRangeBreakout.mqh")

    assert "SetEntryIntentDecision" in text
    assert "MathMin(retestBar.low, breakoutBar.low)" in text
    assert "MathMax(retestBar.high, breakoutBar.high)" in text
    assert "ORB_NO_STOP_LOSS" in text
    assert "m_signalEmittedThisSession" in text
    assert "ORB_SIGNAL_COOLDOWN" in text
    assert "ORB_SESSION_SIGNAL_CAP" in text
    assert "MarkSignalEmitted" in text
    assert "BreakThenRetest" in text


def test_vwap_trend_continuation_has_session_gate_and_zero_volume_skip() -> None:
    text = _read("VWAPTrendContinuation.mqh")

    assert "IsEntrySessionForSymbol" in text
    assert "SIGNAL_SKIP_SESSION" in text
    assert "weightedPriceVolume" in text
    assert "tick_volume" in text
    assert "CalculateClosedBarVwap" in text
    assert "SKIP_DATA_ZERO_VOLUME" in text
    assert "PERIOD_M5" in text


def test_vwap_trend_continuation_requires_stop_loss_and_cooldown() -> None:
    text = _read("VWAPTrendContinuation.mqh")

    assert "SetEntryIntentDecision" in text
    assert "MathMin(priorLow, vwap - buffer)" in text
    assert "MathMax(priorHigh, vwap + buffer)" in text
    assert "VWAP_NO_STOP_LOSS" in text
    assert "VWAP_SIGNAL_COOLDOWN" in text
    assert "CooldownActive" in text
    assert "impulseAtrMultiple" in text
    assert "PULLBACK_NEAR_VWAP" in text
    assert "REJECTION_CLOSE_OK" in text


def test_secondary_strategies_have_objective_monitor_only_intents() -> None:
    expectations = {
        "NoiseBandMomentum.mqh": ["BAND_COMPRESSED", "BAND_BREAK_UP", "BAND_BREAK_DOWN"],
        "LondonNYOverlapMomentum.mqh": [
            "REFERENCE_RANGE_BUILT",
            "RANGE_BREAK_UP",
            "RANGE_BREAK_DOWN",
        ],
        "VolatilityExpansion.mqh": [
            "SETUP_BOX_BUILT",
            "REAL_VOLUME_USED",
            "TICK_VOLUME_USED",
        ],
    }

    for name, markers in expectations.items():
        text = _read(name)
        assert "SetEntryIntentDecision" in text
        assert "SetDecisionContext" in text
        assert "MONITOR_ONLY" not in text.upper() or "monitor-only" in text
        for marker in markers:
            assert marker in text


def test_strategy_modules_do_not_contain_prohibited_logic_terms() -> None:
    strategy_text = "\n".join(
        _read(name)
        for name in [
            "OpeningRangeBreakout.mqh",
            "VWAPTrendContinuation.mqh",
            "NoiseBandMomentum.mqh",
            "LondonNYOverlapMomentum.mqh",
            "VolatilityExpansion.mqh",
        ]
    ).lower()

    for term in [
        "martingale",
        "averaging down",
        "arbitrage",
        "copy trading",
        "tick scalping",
    ]:
        assert term not in strategy_text


def test_phase6_ea_remains_monitor_only_and_account_programs_blocked() -> None:
    text = EA_SOURCE.read_text(encoding="utf-8")
    audit = _read("AuditLogger.mqh")

    assert "Phase 9 strategy intents are signals only" in text
    assert "not approved for Trial, Challenge, Verification, Funded" in text
    assert "Surge 2 Step, Vanguard, or any protected use" in text
    assert "TradeManager refuses execution" in audit
    assert "Surge 2 Step rules are unverified" in audit


def test_phase6_source_scan_passes() -> None:
    result = run_mql5_source_scan(ROOT)

    assert result.status == "PASS"
    assert result.violations == []


def test_phase6_ea_compiles_or_skips_gracefully() -> None:
    result = compile_ea(ROOT)

    assert result.status in {"PASS", "SKIPPED"}
    assert result.log_path


def test_no_order_placement_calls_exist_in_phase6_source() -> None:
    text = _all_mql5_text().lower()
    for pattern in [
        "ordersend(",
        "ctrade",
        ".buy(",
        ".sell(",
        "positionopen(",
        "buylimit(",
        "selllimit(",
        "buystop(",
        "sellstop(",
    ]:
        assert pattern not in text

from __future__ import annotations

import re
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


def test_phase85_source_scan_passes_with_phase9_timezone_implementation() -> None:
    result = run_mql5_source_scan(ROOT)

    assert result.status == "PASS"
    assert result.violations == []
    checks = {check.name: check for check in result.safeguards}
    assert checks["NoCurrentBarSignalDecisions"].status == "PASS"
    assert checks["BrokerServerToNewYorkConversion"].status == "PASS"


def test_phase85_compile_passes_or_skips_gracefully_without_metaeditor() -> None:
    result = compile_ea(ROOT)

    assert result.status in {"PASS", "SKIPPED"}
    assert Path(result.log_path).exists()


def test_phase85_no_order_placement_calls_exist() -> None:
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


def test_phase85_strategy_reason_codes_are_present() -> None:
    expected = {
        "OpeningRangeBreakout.mqh": [
            "ORB_RANGE_BUILT",
            "ORB_WIDTH_OK",
            "BREAK_CLOSE_OUTSIDE",
            "RETEST_PASS",
            "RETEST_FAIL",
            "CLOSE_BACK_INSIDE",
            "LATE_SIGNAL_BLOCK",
            "SPREAD_BLOCK",
            "NEWS_BLOCK",
        ],
        "VWAPTrendContinuation.mqh": [
            "VWAP_BIAS_LONG",
            "VWAP_BIAS_SHORT",
            "VWAP_SLOPE_OK",
            "PULLBACK_NEAR_VWAP",
            "REJECTION_CLOSE_OK",
            "IMPULSE_MISSING",
            "VWAP_FLAT_BLOCK",
            "CHOP_BLOCK",
        ],
        "NoiseBandMomentum.mqh": [
            "BAND_COMPRESSED",
            "BAND_BREAK_UP",
            "BAND_BREAK_DOWN",
            "MOMENTUM_OK",
            "EXPANSION_OK",
            "REENTRY_FAIL",
            "WHIPSAW_BLOCK",
            "VWAP_FLAT_BLOCK",
        ],
        "LondonNYOverlapMomentum.mqh": [
            "OVERLAP_WINDOW_OK",
            "REFERENCE_RANGE_BUILT",
            "RANGE_BREAK_UP",
            "RANGE_BREAK_DOWN",
            "TREND_ALIGN_OK",
            "RETEST_PASS",
            "NEWS_BLOCK",
            "LATE_OVERLAP_BLOCK",
        ],
        "VolatilityExpansion.mqh": [
            "SETUP_BOX_BUILT",
            "CONTRACTION_OK",
            "RANGE_EXPAND_OK",
            "VOLUME_EXPAND_OK",
            "BREAK_UP",
            "BREAK_DOWN",
            "REAL_VOLUME_USED",
            "TICK_VOLUME_USED",
            "EXHAUSTION_BLOCK",
        ],
    }

    for filename, markers in expected.items():
        text = _read(filename)
        for marker in markers:
            assert marker in text


def test_phase85_closed_bar_markers_and_no_current_bar_copyrates() -> None:
    for filename in [
        "OpeningRangeBreakout.mqh",
        "VWAPTrendContinuation.mqh",
        "NoiseBandMomentum.mqh",
        "LondonNYOverlapMomentum.mqh",
        "VolatilityExpansion.mqh",
    ]:
        text = _read(filename)
        assert "UPCOMERS_CLOSED_BAR_SHIFT" in text
        assert "CopyRates" in text
        assert re.search(r"CopyRates\s*\([^;]*,\s*0\s*,", text, re.DOTALL) is None


def test_phase85_orb_m1_minutes_and_retest_mode() -> None:
    text = _read("OpeningRangeBreakout.mqh")

    assert "PERIOD_M1" in text
    assert "OpeningRangeMinutesToM1Bars" in text
    assert "BreakThenRetest" in text
    assert "retestWindowBars" in text
    assert "MathMin(retestBar.low, breakoutBar.low)" in text
    assert "MathMax(retestBar.high, breakoutBar.high)" in text


def test_phase85_vwap_impulse_pullback_rejection_markers() -> None:
    text = _read("VWAPTrendContinuation.mqh")

    assert "PERIOD_M5" in text
    assert "impulseAtrMultiple" in text
    assert "pullbackLong" in text
    assert "pullbackShort" in text
    assert "rejectionLong" in text
    assert "rejectionShort" in text
    assert "CountVwapCrosses" in text


def test_phase85_volume_fallback_and_overlap_defaults() -> None:
    volume = _read("VolatilityExpansion.mqh")
    overlap = _read("LondonNYOverlapMomentum.mqh")

    assert "REAL_VOLUME_USED" in volume
    assert "TICK_VOLUME_USED" in volume
    assert "MedianVolume" in volume
    assert "FX/gold-focused by default" in overlap
    assert "OVERLAP_INDEX_DEFAULT_BLOCK" in overlap


def test_phase85_all_strategy_modules_remain_monitor_only() -> None:
    for filename in [
        "OpeningRangeBreakout.mqh",
        "VWAPTrendContinuation.mqh",
        "NoiseBandMomentum.mqh",
        "LondonNYOverlapMomentum.mqh",
        "VolatilityExpansion.mqh",
    ]:
        text = _read(filename)
        assert "monitor-only" in text
        assert "SetEntryIntentDecision" in text

    trade_manager = _read("TradeManager.mqh")
    assert "RefuseExecution" in trade_manager
    assert "return false" in trade_manager


def test_phase85_trial_surge_and_vanguard_remain_blocked() -> None:
    ea_text = EA_SOURCE.read_text(encoding="utf-8")
    config_text = _read("Config.mqh")
    audit_text = _read("AuditLogger.mqh")

    assert "EnableTrading = false" in ea_text
    assert "EnablePropChallengeMode = false" in ea_text
    assert "Surge 2 Step rules are unverified" in audit_text
    assert "Vanguard remains protected" in audit_text
    assert "AccountProgram rules are unverified" in config_text
    assert "Vanguard blocked until exact rules" in config_text

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


def test_phase9_source_scan_passes_and_broker_time_warning_is_cleared() -> None:
    result = run_mql5_source_scan(ROOT)
    checks = {check.name: check for check in result.safeguards}

    assert result.status == "PASS"
    assert result.violations == []
    assert checks["BrokerServerToNewYorkConversion"].status == "PASS"
    assert checks["BrokerServerToNewYorkConversion"].actual == "implemented"


def test_phase9_session_manager_has_dst_aware_conversion_and_session_helpers() -> None:
    text = _read("SessionManager.mqh")

    for marker in [
        "BrokerServerUtcOffsetMinutes",
        "ConvertBrokerServerToUtc",
        "ConvertUtcToNewYork",
        "IsNewYorkDaylightSavingUtc",
        "NewYorkUtcOffsetMinutesForUtc",
        "NthSundayOfMonth",
        "IsIndexCashSession",
        "IsFxGoldCryptoNYSession",
        "IsLondonNewYorkOverlap",
        "IsNearSessionEnd",
        "SessionTag",
    ]:
        assert marker in text

    assert "UPCOMERS_NY_INDEX_CASH_START_MINUTE 570" in text
    assert "UPCOMERS_NY_INDEX_CASH_END_MINUTE 960" in text
    assert "UPCOMERS_NY_MULTI_ASSET_START_MINUTE 480" in text
    assert "UPCOMERS_NY_OVERLAP_START_MINUTE 480" in text
    assert "UPCOMERS_NY_OVERLAP_LAST_SIGNAL_MINUTE 715" in text
    assert "m_brokerServerUtcOffsetMinutes" in text
    assert "TODO implement DST-aware" not in text


def test_phase9_safe_inputs_exist_for_time_spread_and_throttling() -> None:
    text = EA_SOURCE.read_text(encoding="utf-8")
    config = _read("Config.mqh")

    for marker in [
        "BrokerTimeMode = BROKER_TIME_MANUAL_UTC_OFFSET",
        "BrokerServerUtcOffsetMinutes = 0",
        "RequireBrokerTimeValidation = true",
        'BrokerTimeValidationNote = ""',
        "MaxSpreadPoints = 30",
        "UseSpreadFilter = true",
        "SpreadUnknownBlocksTrading = true",
        "EvaluationMode = EVALUATION_ON_NEW_CLOSED_BAR",
        "MinEvaluationSeconds = 60",
    ]:
        assert marker in text

    assert "BrokerTimeValidationNote required before Trial" in config
    assert "SpreadUnknownBlocksTrading must remain true" in config


def test_phase9_spread_gate_blocks_unknown_or_excessive_spread_by_default() -> None:
    symbol_manager = _read("SymbolManager.mqh")
    ea_text = EA_SOURCE.read_text(encoding="utf-8")

    assert "TryReadSpreadPoints" in symbol_manager
    assert "SYMBOL_SPREAD" in symbol_manager
    assert "SYMBOL_ASK" in symbol_manager
    assert "SYMBOL_BID" in symbol_manager
    assert "SPREAD_UNKNOWN" in symbol_manager
    assert "SpreadUnknownBlocksTrading=true" in symbol_manager
    assert "SPREAD_BLOCK" in symbol_manager
    assert "SIGNAL_SKIP_SPREAD" in ea_text
    assert "SetSkipDecision" in ea_text


def test_phase9_throttling_defaults_avoid_per_tick_repeated_evaluation() -> None:
    state = _read("StateManager.mqh")
    ea_text = EA_SOURCE.read_text(encoding="utf-8")

    assert "ShouldEvaluateMonitorEvent" in state
    assert "GetLatestClosedBarTime" in state
    assert "UPCOMERS_CLOSED_BAR_SHIFT" in state
    assert "THROTTLE_MIN_SECONDS" in state
    assert "THROTTLE_ON_NEW_CLOSED_BAR" in state
    assert "THROTTLE_TIMER_MODE" in state
    assert "g_state.ShouldEvaluateMonitorEvent" in ea_text
    assert "g_state.MarkMonitorEvaluation" in ea_text


def test_phase9_counter_semantics_separate_evaluations_intents_and_server_messages() -> None:
    counter = _read("MessageCounter.mqh")
    trade_manager = _read("TradeManager.mqh")
    ea_text = EA_SOURCE.read_text(encoding="utf-8")

    for marker in [
        "m_monitorEvaluations",
        "m_tradeIntentEvents",
        "m_refusedTradeActions",
        "m_actualServerMessages",
        "CountMonitorEvaluation",
        "RecordTradeIntentEvent",
        "RecordRefusedTradeAction",
        "RecordActualServerMessage",
    ]:
        assert marker in counter

    assert "WAIT/skip/setup evaluations do not count as trade attempts or server messages" in (
        trade_manager
    )
    assert "messageCounter.RecordTradeIntentEvent()" in trade_manager
    assert "messageCounter.RecordRefusedTradeAction()" in trade_manager
    assert "messageCounter.RecordServerMessageRequest()" not in trade_manager
    assert "g_messageCounter.CountMonitorEvaluation()" in ea_text


def test_phase9_closed_bar_only_markers_remain_in_strategy_modules() -> None:
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


def test_phase9_no_order_placement_calls_exist_and_python_is_support_only() -> None:
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

    assert "Python-controlled MT5 execution is quarantined" in Path(
        ROOT / "docs" / "upcomers_native_ea_direction_lock.md"
    ).read_text(encoding="utf-8")


def test_phase9_trial_surge_and_vanguard_remain_blocked() -> None:
    ea_text = EA_SOURCE.read_text(encoding="utf-8")
    config = _read("Config.mqh")
    audit = _read("AuditLogger.mqh")

    assert "EnableTrading = false" in ea_text
    assert "EnablePropChallengeMode = false" in ea_text
    assert "Surge 2 Step rules are unverified" in audit
    assert "Vanguard remains protected" in audit
    assert "AccountProgram rules are unverified" in config
    assert "Vanguard blocked until exact rules" in config


def test_phase9_ea_compiles_or_skips_gracefully() -> None:
    result = compile_ea(ROOT)

    assert result.status in {"PASS", "SKIPPED"}
    assert Path(result.log_path).exists()

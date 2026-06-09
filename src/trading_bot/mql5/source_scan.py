from __future__ import annotations

import re
from pathlib import Path

from trading_bot.mql5.models import Mql5SourceScanReport, SafeguardCheck
from trading_bot.mt5.safety import find_mql5_source_scan_violations

MQL5_SUFFIXES = {".mq5", ".mqh"}
EA_RELATIVE_PATH = Path("Experts/UpcomersNYSessionPropBot/UpcomersNYSessionPropBot.mq5")
TRADE_MANAGER_RELATIVE_PATH = Path("Include/UpcomersNYSessionPropBot/TradeManager.mqh")
TRIAL_EXECUTION_RELATIVE_PATH = Path("Include/UpcomersNYSessionPropBot/TrialExecution.mqh")
TESTER_EXECUTION_RELATIVE_PATH = Path("Include/UpcomersNYSessionPropBot/TesterExecution.mqh")
INCLUDE_RELATIVE_PATH = Path("Include/UpcomersNYSessionPropBot")
STRATEGY_RELATIVE_PATHS = {
    "OpeningRangeBreakout": INCLUDE_RELATIVE_PATH / "OpeningRangeBreakout.mqh",
    "VWAPTrendContinuation": INCLUDE_RELATIVE_PATH / "VWAPTrendContinuation.mqh",
    "NoiseBandMomentum": INCLUDE_RELATIVE_PATH / "NoiseBandMomentum.mqh",
    "LondonNYOverlapMomentum": INCLUDE_RELATIVE_PATH / "LondonNYOverlapMomentum.mqh",
    "VolatilityExpansion": INCLUDE_RELATIVE_PATH / "VolatilityExpansion.mqh",
}


def scan_mql5_source_tree(root: str | Path = ".") -> Mql5SourceScanReport:
    mql5_root = _resolve_mql5_root(Path(root).resolve())
    files = list(_iter_mql5_files(mql5_root)) if mql5_root.exists() else []
    if not files:
        return Mql5SourceScanReport(
            status="SKIPPED",
            root=str(mql5_root),
            message="mql5 source tree does not exist yet",
        )

    violations = find_mql5_source_scan_violations(mql5_root)
    safeguards = evaluate_required_safeguards(mql5_root)
    failed_safeguards = [check for check in safeguards if check.status == "FAIL"]
    status = "FAIL" if violations or failed_safeguards else "PASS"
    return Mql5SourceScanReport(
        status=status,
        root=str(mql5_root),
        message="MQL5 source scan passed"
        if status == "PASS"
        else "MQL5 source scan violations found",
        violations=violations,
        safeguards=safeguards,
    )


def evaluate_required_safeguards(mql5_root: str | Path) -> list[SafeguardCheck]:
    root = Path(mql5_root)
    combined = "\n".join(path.read_text(encoding="utf-8") for path in _iter_mql5_files(root))
    ea_text = _read_optional(root / EA_RELATIVE_PATH)
    trade_manager_text = _read_optional(root / TRADE_MANAGER_RELATIVE_PATH)
    trial_execution_text = _read_optional(root / TRIAL_EXECUTION_RELATIVE_PATH)
    strategy_texts = {
        name: _read_optional(root / relative_path)
        for name, relative_path in STRATEGY_RELATIVE_PATHS.items()
    }
    checks = [
        _bool_input_check(ea_text, "EnableTrading", False),
        _bool_input_check(ea_text, "EnableTrialExecution", False),
        _bool_input_check(ea_text, "StrategyTesterExecutionMode", False),
        _bool_input_check(ea_text, "EnablePropChallengeMode", False),
        _enum_input_check(
            ea_text,
            "AccountProgram",
            "ACCOUNT_PROGRAM_TRIAL_RISK_FREE",
        ),
        _bool_input_check(ea_text, "RequireManualConfirmationText", True),
        _numeric_input_check(ea_text, "MinHoldSeconds", 180.0, operator=">="),
        _numeric_input_check(ea_text, "MaxDailyLossHardPct", 4.0, operator="<"),
        _numeric_input_check(ea_text, "MaxOverallLossHardPct", 7.0, operator="<"),
        _numeric_input_check(ea_text, "MaxRiskPerTradePct", 0.50, operator="<="),
        _bool_input_check(ea_text, "StopLossRequired", True),
        _numeric_input_check(ea_text, "MaxTradesPerDay", 1.0, operator="<="),
        _numeric_input_check(ea_text, "MaxServerMessagesPerDay", 2000.0, operator="<="),
        _numeric_input_check(ea_text, "MaxOpenPositionsTotal", 1.0, operator="<="),
        _string_input_check(ea_text, "AllowedSymbols", "EURUSD"),
        _enum_input_check(ea_text, "BrokerTimeMode", "BROKER_TIME_MANUAL_UTC_OFFSET"),
        _numeric_input_check(ea_text, "BrokerServerUtcOffsetMinutes", 840.0, operator="<="),
        _bool_input_check(ea_text, "RequireBrokerTimeValidation", True),
        _bool_input_check(ea_text, "UseSpreadFilter", True),
        _numeric_input_check(ea_text, "MaxSpreadPoints", 0.0, operator=">"),
        _bool_input_check(ea_text, "SpreadUnknownBlocksTrading", True),
        _enum_input_check(ea_text, "EvaluationMode", "EVALUATION_ON_NEW_CLOSED_BAR"),
        _numeric_input_check(ea_text, "MinEvaluationSeconds", 1.0, operator=">="),
        _trade_manager_refusal_check(trade_manager_text),
        _trial_execution_isolation_check(root),
        _trial_execution_gate_check(trial_execution_text),
        _tester_execution_gate_check(_read_optional(root / TESTER_EXECUTION_RELATIVE_PATH)),
        _no_current_bar_decision_check(strategy_texts),
        _combined_token_check(
            combined,
            "closed_bar_only_markers",
            "UPCOMERS_CLOSED_BAR_SHIFT",
            "strategies must mark closed-bar-only signal evaluation",
        ),
        _strategy_token_check(
            strategy_texts,
            "OpeningRangeBreakout",
            "orb_m1_minutes_to_bars",
            ("PERIOD_M1", "OpeningRangeMinutesToM1Bars", "closed M1 bars"),
            "ORB must build the range from M1 bars and convert minutes to bars",
        ),
        _strategy_token_check(
            strategy_texts,
            "OpeningRangeBreakout",
            "orb_break_then_retest_mode",
            ("BreakThenRetest", "RETEST_PASS", "RETEST_FAIL", "BREAK_CLOSE_OUTSIDE"),
            "ORB must default to break-then-retest with explicit reason codes",
        ),
        _strategy_token_check(
            strategy_texts,
            "VWAPTrendContinuation",
            "vwap_impulse_pullback_rejection",
            (
                "PERIOD_M5",
                "impulseAtrMultiple",
                "PULLBACK_NEAR_VWAP",
                "REJECTION_CLOSE_OK",
                "VWAP_SLOPE_OK",
            ),
            "VWAP continuation must require impulse, pullback, slope, and rejection markers",
        ),
        _strategy_token_check(
            strategy_texts,
            "VolatilityExpansion",
            "volume_type_logging",
            ("REAL_VOLUME_USED", "TICK_VOLUME_USED", "MedianVolume", "VolumeTypeUsed"),
            "volume expansion must log real-volume or tick-volume fallback",
        ),
        _combined_token_check(
            combined,
            "per_session_strategy_signal_caps",
            "MaxSignalsPerStrategyPerSession",
            "strategy signal caps must exist per strategy/session",
        ),
        _timezone_conversion_check(combined),
        _combined_token_check(
            combined,
            "session_manager_phase9_helpers",
            "IsFxGoldCryptoNYSession",
            "Phase 9 session helpers must include FX/gold/crypto New York session checks",
        ),
        _combined_token_check(
            combined,
            "session_half_hour_boundary",
            "UPCOMERS_NY_INDEX_CASH_START_MINUTE 570",
            "index cash session must represent the 09:30 New York half-hour boundary",
        ),
        _combined_token_check(
            combined,
            "spread_gate",
            "SPREAD_BLOCK",
            "real spread gate must block excessive or unknown spreads by default",
        ),
        _combined_token_check(
            combined,
            "evaluation_throttle",
            "THROTTLE_ON_NEW_CLOSED_BAR",
            "OnTick/OnTimer evaluation throttling must avoid repeated per-tick evaluations",
        ),
        _combined_token_check(
            combined,
            "counter_semantics",
            "WAIT/skip/setup evaluations do not count as trade attempts or server messages",
            (
                "monitor counters must separate evaluations, intents, refused actions, "
                "and server messages"
            ),
        ),
        _combined_token_check(
            combined,
            "python_support_only_marker",
            "TradeManager refuses execution",
            "strategy modules log monitor-only intents and TradeManager refuses execution",
        ),
        _combined_token_check(
            combined,
            "trial_execution_confirmation_phrase",
            "I_ACCEPT_TRIAL_RISK_FREE_EXECUTION_ONLY",
            "Trial execution requires the strict manual confirmation phrase",
        ),
        _combined_token_check(
            combined,
            "trial_execution_no_retry",
            "NO_RETRY_ORDER_SEND_ONCE",
            "Trial execution must send no more than one order request per signal",
        ),
        _combined_token_check(
            combined,
            "strategy_tester_execution_runtime_gate",
            "MQL_TESTER",
            "Strategy Tester execution must require MT5 tester runtime detection",
        ),
        _combined_token_check(
            combined,
            "strategy_tester_signal_diagnostics",
            "STRATEGY_DIAGNOSTICS_SUMMARY",
            "Strategy Tester runs must emit final signal diagnostics summaries",
        ),
    ]
    return checks


def _resolve_mql5_root(root: Path) -> Path:
    if root.name.lower() == "mql5":
        return root
    return root / "mql5"


def _iter_mql5_files(root: Path):
    if not root.exists():
        return
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in MQL5_SUFFIXES:
            yield path


def _read_optional(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _input_value(text: str, name: str) -> str | None:
    pattern = re.compile(rf"input\s+[\w_]+\s+{re.escape(name)}\s*=\s*([^;]+);")
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _bool_input_check(text: str, name: str, expected: bool) -> SafeguardCheck:
    raw = _input_value(text, name)
    expected_text = "true" if expected else "false"
    if raw is None:
        return SafeguardCheck(name, "FAIL", expected_text, "missing", f"missing {name}")
    actual = raw.lower()
    status = "PASS" if actual == expected_text else "FAIL"
    return SafeguardCheck(
        name=name,
        status=status,
        expected=expected_text,
        actual=actual,
        message=f"{name} default is {actual}",
    )


def _enum_input_check(text: str, name: str, expected: str) -> SafeguardCheck:
    raw = _input_value(text, name)
    if raw is None:
        return SafeguardCheck(name, "FAIL", expected, "missing", f"missing {name}")
    status = "PASS" if raw == expected else "FAIL"
    return SafeguardCheck(
        name=name,
        status=status,
        expected=expected,
        actual=raw,
        message=f"{name} default is {raw}",
    )


def _numeric_input_check(
    text: str,
    name: str,
    threshold: float,
    *,
    operator: str,
) -> SafeguardCheck:
    raw = _input_value(text, name)
    if raw is None:
        return SafeguardCheck(
            name,
            "FAIL",
            f"{operator} {threshold:g}",
            "missing",
            f"missing {name}",
        )
    try:
        actual = float(raw)
    except ValueError:
        return SafeguardCheck(name, "FAIL", f"{operator} {threshold:g}", raw, "not numeric")
    if operator == ">=":
        passed = actual >= threshold
    elif operator == "<":
        passed = actual < threshold
    elif operator == "<=":
        passed = actual <= threshold
    elif operator == ">":
        passed = actual > threshold
    else:
        raise ValueError(f"unsupported operator {operator}")
    return SafeguardCheck(
        name=name,
        status="PASS" if passed else "FAIL",
        expected=f"{operator} {threshold:g}",
        actual=f"{actual:g}",
        message=f"{name} default {actual:g} must be {operator} {threshold:g}",
    )


def _string_input_check(text: str, name: str, expected: str) -> SafeguardCheck:
    raw = _input_value(text, name)
    if raw is None:
        return SafeguardCheck(name, "FAIL", expected, "missing", f"missing {name}")
    actual = raw.strip('"')
    status = "PASS" if actual == expected else "FAIL"
    return SafeguardCheck(
        name=name,
        status=status,
        expected=expected,
        actual=actual,
        message=f"{name} default is {actual}",
    )


def _trade_manager_refusal_check(text: str) -> SafeguardCheck:
    lowered = text.lower()
    passed = (
        "refuseexecution" in lowered
        and "return false" in lowered
        and "no-trade trademanager" in lowered
        and "ordersend" not in lowered
        and "ctrade" not in lowered
        and ".buy(" not in lowered
        and ".sell(" not in lowered
    )
    return SafeguardCheck(
        name="TradeManagerRefusalOnly",
        status="PASS" if passed else "FAIL",
        expected="refusal-only without order calls",
        actual="refusal-only" if passed else "unsafe or incomplete",
        message="TradeManager must refuse execution until an explicitly approved execution phase",
    )


def _trial_execution_isolation_check(root: Path) -> SafeguardCheck:
    order_patterns = {
        "ordersend(",
        "ctrade",
        ".buy(",
        ".sell(",
        "positionopen(",
        "buylimit(",
        "selllimit(",
        "buystop(",
        "sellstop(",
    }
    offenders: list[str] = []
    for path in _iter_mql5_files(root):
        relative = _relative(path, root)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            compact = "".join(line.lower().split())
            if any(pattern in compact for pattern in order_patterns) and relative not in {
                TRIAL_EXECUTION_RELATIVE_PATH,
                TESTER_EXECUTION_RELATIVE_PATH,
            }:
                offenders.append(f"{relative}:{line_number}")
    return SafeguardCheck(
        name="TrialExecutionOrderCallIsolation",
        status="PASS" if not offenders else "FAIL",
        expected=str(TRIAL_EXECUTION_RELATIVE_PATH),
        actual=", ".join(offenders) if offenders else "isolated",
        message=(
            "MQL5 order calls are allowed only inside isolated TrialExecution "
            "or TesterExecution modules"
        ),
    )


def _trial_execution_gate_check(text: str) -> SafeguardCheck:
    lowered = text.lower()
    required_tokens = (
        "ordersend(request, result)",
        "validatetrialexecutionconfig",
        "account_program_trial_risk_free",
        "account_stage_trial",
        "enabletrialexecution",
        "enabletrading",
        "enablepropchallengemode",
        "hastrialexecutionconfirmation",
        "sourcescanpassid",
        "stoplossrequired",
        "minholdseconds",
        "maxriskpertradepct",
        "riskpertradepct",
        "maxopenpositionstotal",
        "maxopenpositionspersymbol",
        "maxtradesperday",
        "maxservermessagesperday",
        "allowedsymbols",
        "usespreadfilter",
        "requirebrokertimevalidation",
        "brokertimevalidationnote",
        "maxspreadpoints",
        "hasstoploss",
        "hastakeprofit",
        "symbol_trade_stops_level",
        "symbol_point",
        "stop_level_constraint",
        "trade_action_deal",
        "no_retry_order_send_once",
        "no_action_signal_not_executable",
        "armed_trial_execution_waiting_for_valid_signal",
    )
    missing = [token for token in required_tokens if token not in lowered]
    return SafeguardCheck(
        name="TrialExecutionOrderGates",
        status="PASS" if not missing else "FAIL",
        expected=", ".join(required_tokens),
        actual="present" if not missing else f"missing: {', '.join(missing)}",
        message="Trial execution order calls must be guarded by TrialRiskFree-only safety checks",
    )


def _tester_execution_gate_check(text: str) -> SafeguardCheck:
    lowered = text.lower()
    required_tokens = (
        "ordersend(request, result)",
        "validatestrategytesterexecutionconfig",
        "tester_execution_summary",
        "tester_gate_fail",
        "tester_entry_intent_received",
        "tester_order_request",
        "tester_order_normalized",
        "volume_normalized_to_min_step",
        "symbol_filling_mode",
        "request.type_filling",
        "tester_execution_order_rejected",
        "mql_tester",
        "strategytesterexecutionmode",
        "enabletradinginputfalse",
        "enabletrialexecutionfalse",
        "enablepropchallengemodefalse",
        "account_program_trial_risk_free",
        "account_stage_monitor_only",
        "allowedsymbols",
        "stoplossrequired",
        "minholdseconds",
        "usespreadfilter",
        "maxspreadpoints",
        "hasstoploss",
        "hastakeprofit",
        "symbol_trade_stops_level",
        "symbol_point",
        "stop_level_constraint",
        "trade_action_deal",
        "tester_no_retry_order_send_once",
        "tester_no_action_signal_not_executable",
    )
    missing = [token for token in required_tokens if token not in lowered]
    return SafeguardCheck(
        name="TesterExecutionOrderGates",
        status="PASS" if not missing else "FAIL",
        expected=", ".join(required_tokens),
        actual="present" if not missing else f"missing: {', '.join(missing)}",
        message=(
            "Strategy Tester simulated order calls must be isolated and guarded by "
            "tester-runtime-only checks"
        ),
    )


def _no_current_bar_decision_check(strategy_texts: dict[str, str]) -> SafeguardCheck:
    offenders: list[str] = []
    current_bar_copy = re.compile(r"CopyRates\s*\([^;]*,\s*0\s*,", re.IGNORECASE | re.DOTALL)
    current_bar_close = re.compile(r"rates\s*\[\s*0\s*\]\s*\.\s*close", re.IGNORECASE)
    for name, text in strategy_texts.items():
        if current_bar_copy.search(text):
            offenders.append(f"{name}:CopyRates start_pos 0")
        if current_bar_close.search(text) and "UPCOMERS_CLOSED_BAR_SHIFT" not in text:
            offenders.append(f"{name}:rates[0].close without closed-bar shift marker")
    passed = not offenders
    return SafeguardCheck(
        name="NoCurrentBarSignalDecisions",
        status="PASS" if passed else "FAIL",
        expected="closed-bar CopyRates start and closed-bar marker",
        actual=", ".join(offenders) if offenders else "closed-bar-only markers present",
        message="strategy signal state changes must not use the unfinished current candle",
    )


def _strategy_token_check(
    strategy_texts: dict[str, str],
    strategy_name: str,
    name: str,
    expected_tokens: tuple[str, ...],
    message: str,
) -> SafeguardCheck:
    text = strategy_texts.get(strategy_name, "")
    lowered = text.lower()
    missing = [token for token in expected_tokens if token.lower() not in lowered]
    return SafeguardCheck(
        name=name,
        status="PASS" if not missing else "FAIL",
        expected=", ".join(expected_tokens),
        actual="present" if not missing else f"missing: {', '.join(missing)}",
        message=message,
    )


def _timezone_conversion_check(combined: str) -> SafeguardCheck:
    lowered = combined.lower()
    has_old_stub = (
        "tryconvertbrokerservertonewyork" in lowered
        and "todo implement dst-aware" in lowered
    )
    required_tokens = (
        "brokerserverutcoffsetminutes",
        "convertbrokerservertoutc",
        "convertutctonewyork",
        "isnewyorkdaylightsavingutc",
        "newyorkutcoffsetminutesforutc",
        "nthsundayofmonth",
    )
    missing = [token for token in required_tokens if token not in lowered]
    passed = not missing and not has_old_stub
    return SafeguardCheck(
        name="BrokerServerToNewYorkConversion",
        status="PASS" if passed else "FAIL",
        expected="explicit broker UTC offset plus DST-aware America/New_York conversion",
        actual="implemented" if passed else f"missing: {', '.join(missing)}",
        message=(
            "broker-server-time to America/New_York conversion must be implemented before "
            "Trial observation plumbing can pass source scan"
        ),
    )


def _combined_token_check(
    combined: str,
    name: str,
    expected: str,
    message: str,
) -> SafeguardCheck:
    passed = expected.lower() in combined.lower()
    return SafeguardCheck(
        name=name,
        status="PASS" if passed else "FAIL",
        expected=expected,
        actual="present" if passed else "missing",
        message=message,
    )


def _relative(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path

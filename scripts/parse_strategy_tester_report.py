from __future__ import annotations

import argparse
import html
import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SUPPORTED_SUFFIXES = {".htm", ".html", ".xml", ".csv", ".log", ".txt", ".json", ".set", ".ini"}
RAW_LOG_RE = re.compile(r"\b\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\b")
HTML_TAG_RE = re.compile(r"<[^>]+>")
NUMERIC_VALUE_RE = r"([-+]?\d[\d, ]*(?:\.\d+)?)"
COUNT_PATTERNS = {
    "trades": (
        re.compile(r"\btotal\s+trades\b\s*[:=]?\s*(\d+)", re.IGNORECASE),
        re.compile(r"\btrades\b\s*[:=]\s*(\d+)", re.IGNORECASE),
        re.compile(r"\btrades\s+total\b\s*[:=]?\s*(\d+)", re.IGNORECASE),
    ),
    "orders": (
        re.compile(r"\borders\b\s*[:=]\s*(\d+)", re.IGNORECASE),
        re.compile(r"\border\s+count\b\s*[:=]?\s*(\d+)", re.IGNORECASE),
        re.compile(r"\borders\s+opened\b\s*[:=]?\s*(\d+)", re.IGNORECASE),
    ),
    "deals": (
        re.compile(r"\bdeals\b\s*[:=]\s*(\d+)", re.IGNORECASE),
        re.compile(r"\bdeal\s+count\b\s*[:=]?\s*(\d+)", re.IGNORECASE),
    ),
}
SETTING_RE = re.compile(
    r"\b(Preset|PresetName|preset_name|EnableTrading|EnableTrialExecution|"
    r"StrategyTesterExecutionMode|"
    r"EnablePropChallengeMode|AccountProgram|AccountStage|StrategySelection|"
    r"StrategyTimeframe|LogThrottleSkips)\b\s*[:=]?\s*([A-Za-z0-9_./-]+)",
    re.IGNORECASE,
)
DIAGNOSTICS_SUMMARY_RE = re.compile(
    r"\bSTRATEGY_DIAGNOSTICS_SUMMARY\b\s*(.*)",
    re.IGNORECASE,
)
TESTER_EXECUTION_SUMMARY_RE = re.compile(
    r"\bTESTER_EXECUTION_SUMMARY\b\s*(.*)",
    re.IGNORECASE,
)
DIAGNOSTICS_KEY_VALUE_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)")
TESTER_GATE_FAIL_RE = re.compile(
    r"\bTESTER_GATE_FAIL_([A-Za-z0-9_]+)\b(?:\s+detail=([^\n\r]+))?",
    re.IGNORECASE,
)
TESTER_RETCODE_RE = re.compile(r"\bretcode[=:](\d+)", re.IGNORECASE)
TESTER_COMMENT_RE = re.compile(
    r"\bcomment=([^=\n\r]+?)(?:\s+no_retry|\s+no retry|\s+request\.|\s+SYMBOL_|\s*$)",
    re.IGNORECASE,
)
PERFORMANCE_PATTERNS = {
    "initial_balance": (
        re.compile(
            rf"\b(?:initial\s+(?:deposit|balance)|starting\s+balance|deposit)\b\s*[:=]?\s*{NUMERIC_VALUE_RE}",
            re.IGNORECASE,
        ),
    ),
    "final_balance": (
        re.compile(rf"\bfinal\s+balance\b\s*[:=]?\s*{NUMERIC_VALUE_RE}", re.IGNORECASE),
        re.compile(rf"^\s*balance\b\s*[:=]?\s*{NUMERIC_VALUE_RE}", re.IGNORECASE | re.MULTILINE),
    ),
    "net_profit": (
        re.compile(
            rf"\b(?:total\s+net\s+profit|net\s+profit)\b\s*[:=]?\s*{NUMERIC_VALUE_RE}",
            re.IGNORECASE,
        ),
    ),
    "profit_factor": (
        re.compile(r"\bprofit\s+factor\b\s*[:=]?\s*([-+]?\d+(?:\.\d+)?)", re.IGNORECASE),
    ),
    "drawdown": (
        re.compile(r"\b(?:maximal\s+)?drawdown\b\s*[:=]?\s*([^\n\r]+)", re.IGNORECASE),
    ),
    "expected_payoff": (
        re.compile(
            r"\bexpected\s+payoff\b\s*[:=]?\s*([-+]?\d+(?:\.\d+)?)",
            re.IGNORECASE,
        ),
    ),
    "average_hold_time": (
        re.compile(r"\baverage\s+hold(?:ing)?\s+time\b\s*[:=]?\s*([^\n\r]+)", re.IGNORECASE),
    ),
}
HOLD_TIME_PATTERNS = (
    re.compile(
        r"\b(?:hold|holding|duration)(?:\s+time)?\b\s*[:=]\s*(\d{1,2}):(\d{2}):(\d{2})",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:hold|holding|duration)(?:\s+seconds?)?\b\s*[:=]\s*(\d+)\s*(?:s|sec|secs|seconds)\b",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True)
class StrategyTesterParseResult:
    status: str
    files: list[str]
    missing_paths: list[str] = field(default_factory=list)
    unsupported_files: list[str] = field(default_factory=list)
    test_period: str = ""
    symbol: str = ""
    timeframe: str = ""
    modeling_mode: str = ""
    input_settings: dict[str, str] = field(default_factory=dict)
    activity_counts: dict[str, int | None] = field(default_factory=dict)
    performance_metrics: dict[str, str | int | float | None] = field(default_factory=dict)
    strategy_diagnostics: dict[str, Any] = field(default_factory=dict)
    tester_execution_summary: dict[str, Any] = field(default_factory=dict)
    diagnostics_assessment: str = ""
    sub_180_second_closes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ea_log_excerpts: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_strategy_tester_report(
    paths: Sequence[str | Path] | str | Path | None,
    *,
    monitor_only: bool = True,
) -> StrategyTesterParseResult:
    selected_paths = _normalize_paths(paths)
    files, missing_paths, unsupported_files = _resolve_files(selected_paths)
    if not selected_paths or not files:
        return StrategyTesterParseResult(
            status="WARN",
            files=[],
            missing_paths=[str(path) for path in missing_paths],
            unsupported_files=[str(path) for path in unsupported_files],
            activity_counts={"trades": None, "orders": None, "deals": None},
            performance_metrics={},
            warnings=["tester_report_missing"],
            message="Strategy Tester report/log files missing or unsupported",
        )

    text_parts = [_read_text(path) for path in files]
    combined = "\n".join(part for part in text_parts if part)
    normalized = _normalize_report_text(combined)
    if not normalized.strip():
        return StrategyTesterParseResult(
            status="WARN",
            files=[str(path) for path in files],
            missing_paths=[str(path) for path in missing_paths],
            unsupported_files=[str(path) for path in unsupported_files],
            activity_counts={"trades": None, "orders": None, "deals": None},
            performance_metrics={},
            warnings=["tester_report_empty_or_binary"],
            message="Strategy Tester files could not be read as text",
        )

    activity_counts = _activity_counts(normalized)
    input_settings = _input_settings(normalized)
    performance_metrics = _performance_metrics(normalized, activity_counts)
    strategy_diagnostics = _strategy_diagnostics(normalized)
    tester_execution_summary = _tester_execution_summary(normalized)
    diagnostics_assessment = _diagnostics_assessment(
        activity_counts,
        strategy_diagnostics,
        tester_execution_summary,
    )
    sub_180_second_closes = _sub_180_second_closes(normalized)
    errors, warnings = _errors_and_warnings(normalized)
    warnings.extend(
        _input_setting_warnings(
            input_settings,
            preset_hint=_preset_hint(input_settings, files),
        )
    )
    if diagnostics_assessment == "no executable entry signals generated":
        warnings.append("no_executable_entry_signals_generated")
    elif diagnostics_assessment == "entry intents did not reach tester order request":
        warnings.append("tester_entry_intents_blocked_by_gate")
    elif diagnostics_assessment == "tester orders attempted but report shows zero trades":
        warnings.append("tester_orders_attempted_without_report_trades")
    elif diagnostics_assessment == "execution gate blocked entries":
        warnings.append("entry_intents_without_trades_execution_gate_blocked")

    status = "PASS"
    message = "monitor-only Strategy Tester evidence parsed with zero detected activity"
    if monitor_only and _has_positive_activity(activity_counts):
        status = "FAIL"
        message = "monitor-only Strategy Tester evidence contains trade/order/deal activity"
    elif _has_failing_warning(warnings):
        status = "FAIL"
        message = "Strategy Tester inputs are unsafe or internally inconsistent"
    elif not monitor_only and sub_180_second_closes:
        status = "FAIL"
        warnings.append("sub_180_second_closes_detected")
        message = "Strategy Tester simulated execution has closes under MinHoldSeconds"
    elif not any(value is not None for value in activity_counts.values()):
        status = "WARN"
        warnings.append("activity_counts_unknown")
        message = "Strategy Tester format parsed, but trade/order/deal counts were not found"
    elif errors:
        status = "WARN"
        message = "Strategy Tester evidence parsed with errors/warnings requiring review"
    elif not monitor_only:
        message = "Strategy Tester simulated execution report parsed"

    if not monitor_only:
        warnings.append("simulated_execution_parse_requested")
        if diagnostics_assessment:
            detail = _tester_gate_reason_text(tester_execution_summary)
            message = f"{message}; {diagnostics_assessment}{detail}"

    return StrategyTesterParseResult(
        status=status,
        files=[str(path) for path in files],
        missing_paths=[str(path) for path in missing_paths],
        unsupported_files=[str(path) for path in unsupported_files],
        test_period=_first_match(
            normalized,
            (
                r"\btest\s+period\b\s*[:=]?\s*([^\n\r]+)",
                r"\bperiod\b\s*[:=]?\s*(\d{4}[^\n\r]+?\d{4}[^\n\r]*)",
            ),
        ),
        symbol=_first_match(normalized, (r"\bsymbol\b\s*[:=]?\s*([A-Za-z0-9._#-]+)",)),
        timeframe=_first_match(
            normalized,
            (
                r"\btimeframe\b\s*[:=]?\s*(M\d+|H\d+|D1|W1|MN1)",
                r"\bperiod\b\s*[:=]?\s*(M\d+|H\d+|D1|W1|MN1)",
            ),
        ),
        modeling_mode=_modeling_mode(normalized),
        input_settings=input_settings,
        activity_counts=activity_counts,
        performance_metrics=performance_metrics,
        strategy_diagnostics=strategy_diagnostics,
        tester_execution_summary=tester_execution_summary,
        diagnostics_assessment=diagnostics_assessment,
        sub_180_second_closes=sub_180_second_closes,
        errors=errors,
        warnings=warnings,
        ea_log_excerpts=_ea_log_excerpts(normalized),
        message=message,
    )


def _normalize_paths(paths: Sequence[str | Path] | str | Path | None) -> list[Path]:
    if paths is None:
        return []
    if isinstance(paths, str | Path):
        return [Path(paths)]
    return [Path(path) for path in paths]


def _resolve_files(paths: Sequence[Path]) -> tuple[list[Path], list[Path], list[Path]]:
    files: list[Path] = []
    missing: list[Path] = []
    unsupported: list[Path] = []
    for path in paths:
        if not path.exists():
            missing.append(path)
            continue
        candidates = [path] if path.is_file() else [item for item in path.rglob("*")]
        for candidate in candidates:
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() in SUPPORTED_SUFFIXES:
                files.append(candidate)
            else:
                unsupported.append(candidate)
    return sorted(files), missing, sorted(unsupported)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _normalize_report_text(text: str) -> str:
    unescaped = html.unescape(text)
    without_tags = HTML_TAG_RE.sub("\n", unescaped)
    return "\n".join(line.strip() for line in without_tags.splitlines() if line.strip())


def _activity_counts(text: str) -> dict[str, int | None]:
    counts = {
        name: _count_from_patterns(text, patterns)
        for name, patterns in COUNT_PATTERNS.items()
    }
    lowered = text.lower()
    if counts["trades"] is None and ("no trades" in lowered or "zero trades" in lowered):
        counts["trades"] = 0
    if counts["orders"] is None and ("no orders" in lowered or "zero orders" in lowered):
        counts["orders"] = 0
    if counts["deals"] is None and ("no deals" in lowered or "zero deals" in lowered):
        counts["deals"] = 0
    return counts


def _count_from_patterns(text: str, patterns: Iterable[re.Pattern[str]]) -> int | None:
    values: list[int] = []
    for pattern in patterns:
        values.extend(int(match.group(1)) for match in pattern.finditer(text))
    return max(values) if values else None


def _has_positive_activity(counts: dict[str, int | None]) -> bool:
    return any(value is not None and value > 0 for value in counts.values())


def _input_settings(text: str) -> dict[str, str]:
    settings: dict[str, str] = {}
    for match in SETTING_RE.finditer(text):
        settings[match.group(1)] = match.group(2)
    return settings


def _input_setting_warnings(settings: dict[str, str], *, preset_hint: str = "") -> list[str]:
    warnings: list[str] = []
    if _setting_value(settings, "EnableTrading").lower() == "true":
        warnings.append("enable_trading_unsafe")
    if _setting_value(settings, "EnableTrialExecution").lower() == "true":
        warnings.append("enable_trial_execution_unsafe")
    if _setting_value(settings, "EnablePropChallengeMode").lower() == "true":
        warnings.append("enable_prop_challenge_mode_unsafe")
    strategy_selection = _setting_value(settings, "StrategySelection").upper()
    if "vwap" in preset_hint.lower() and strategy_selection == "STRATEGY_OPENING_RANGE_BREAKOUT":
        warnings.append("vwap_preset_selects_orb")
    return warnings


def _setting_value(settings: dict[str, str], name: str) -> str:
    for key, value in settings.items():
        if key.lower() == name.lower():
            return value
    return ""


def _preset_hint(settings: dict[str, str], files: Sequence[Path]) -> str:
    configured = " ".join(
        value
        for key, value in settings.items()
        if key.lower() in {"preset", "presetname", "preset_name"}
    )
    file_hint = " ".join(path.name for path in files)
    return f"{configured} {file_hint}"


def _has_failing_warning(warnings: Sequence[str]) -> bool:
    failing = {"vwap_preset_selects_orb"}
    return any(key.endswith("_unsafe") or key in failing for key in warnings)


def _strategy_diagnostics(text: str) -> dict[str, Any]:
    summary_lines = [
        match.group(0).strip()
        for match in DIAGNOSTICS_SUMMARY_RE.finditer(text)
    ]
    if not summary_lines:
        return {}

    latest = summary_lines[-1]
    fields = {
        match.group(1): match.group(2)
        for match in DIAGNOSTICS_KEY_VALUE_RE.finditer(latest)
    }
    reason_counts = _reason_counts(fields.get("top_reason_codes", ""))
    diagnostics: dict[str, Any] = {
        "present": True,
        "summary_lines": summary_lines,
        "strategy": fields.get("strategy", ""),
        "total_evaluations": _int_or_none(fields.get("total_evaluations")),
        "enter_long": _int_or_none(fields.get("enter_long")) or 0,
        "enter_short": _int_or_none(fields.get("enter_short")) or 0,
        "tester_execution_mode": fields.get("tester_execution_mode", ""),
        "tester_runtime": fields.get("tester_runtime", ""),
        "tester_orders_attempted": _int_or_none(fields.get("tester_orders_attempted")) or 0,
        "reason_counts": reason_counts,
    }
    return diagnostics


def _tester_execution_summary(text: str) -> dict[str, Any]:
    summary_lines = [
        match.group(0).strip()
        for match in TESTER_EXECUTION_SUMMARY_RE.finditer(text)
    ]
    gate_failure_details = _tester_gate_failure_details(text)
    rejection_details = _tester_rejection_details(text)
    rejection_summary = _tester_rejection_summary(rejection_details)
    if not summary_lines and not gate_failure_details and not rejection_details:
        return {}

    fields: dict[str, str] = {}
    if summary_lines:
        fields = {
            match.group(1): match.group(2)
            for match in DIAGNOSTICS_KEY_VALUE_RE.finditer(summary_lines[-1])
        }
    gate_failure_counts = _reason_counts(fields.get("top_tester_gate_failures", ""))
    return {
        "present": bool(summary_lines),
        "summary_lines": summary_lines,
        "tester_entry_intents_received": (
            _int_or_none(fields.get("tester_entry_intents_received")) or 0
        ),
        "tester_orders_attempted": _int_or_none(fields.get("tester_orders_attempted")) or 0,
        "tester_orders_sent_success": (
            _int_or_none(fields.get("tester_orders_sent_success")) or 0
        ),
        "tester_orders_rejected": _int_or_none(fields.get("tester_orders_rejected")) or 0,
        "tester_orders_skipped_by_gate": (
            _int_or_none(fields.get("tester_orders_skipped_by_gate")) or 0
        ),
        "last_tester_gate_failure": fields.get("last_tester_gate_failure", ""),
        "gate_failure_counts": gate_failure_counts,
        "gate_failure_details": gate_failure_details,
        "rejection_details": rejection_details,
        "rejection_retcode_counts": rejection_summary["retcode_counts"],
        "rejection_comment_counts": rejection_summary["comment_counts"],
    }


def _tester_gate_failure_details(text: str) -> list[str]:
    details: list[str] = []
    for line in text.splitlines():
        match = TESTER_GATE_FAIL_RE.search(line)
        if not match:
            continue
        gate_name = match.group(1)
        detail = (match.group(2) or "").strip()
        details.append(f"{gate_name}: {detail}"[:300])
        if len(details) >= 25:
            break
    return details


def _tester_rejection_details(text: str) -> list[str]:
    details: list[str] = []
    for line in text.splitlines():
        lowered = line.lower()
        if (
            "tester_execution_order_rejected" in lowered
            or "tester_execution_broker_response" in lowered
        ):
            details.append(line[:300])
        if len(details) >= 25:
            break
    return details


def _tester_rejection_summary(details: Sequence[str]) -> dict[str, dict[str, int]]:
    retcode_counts: dict[str, int] = {}
    comment_counts: dict[str, int] = {}
    for line in details:
        for match in TESTER_RETCODE_RE.finditer(line):
            retcode = match.group(1)
            retcode_counts[retcode] = retcode_counts.get(retcode, 0) + 1
        comment_match = TESTER_COMMENT_RE.search(line)
        if comment_match:
            comment = " ".join(comment_match.group(1).strip().split())
            if comment:
                comment_counts[comment] = comment_counts.get(comment, 0) + 1
    return {
        "retcode_counts": retcode_counts,
        "comment_counts": comment_counts,
    }


def _reason_counts(summary: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in summary.split("|"):
        if not item:
            continue
        if ":" in item:
            key, raw_value = item.split(":", 1)
        elif "=" in item:
            key, raw_value = item.split("=", 1)
        else:
            continue
        value = _int_or_none(raw_value)
        if value is not None:
            counts[key] = value
    return counts


def _int_or_none(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _diagnostics_assessment(
    activity_counts: dict[str, int | None],
    diagnostics: dict[str, Any],
    tester_execution: dict[str, Any],
) -> str:
    if not diagnostics:
        return ""
    trades = activity_counts.get("trades")
    if trades is None or trades != 0:
        return ""
    enter_long = int(diagnostics.get("enter_long") or 0)
    enter_short = int(diagnostics.get("enter_short") or 0)
    entry_intents = enter_long + enter_short
    tester_orders_attempted = int(
        tester_execution.get(
            "tester_orders_attempted",
            diagnostics.get("tester_orders_attempted") or 0,
        )
        or 0
    )
    if enter_long == 0 and enter_short == 0:
        return "no executable entry signals generated"
    if entry_intents > 0 and tester_orders_attempted == 0 and tester_execution:
        return "entry intents did not reach tester order request"
    if entry_intents > 0 and tester_orders_attempted == 0:
        return "execution gate blocked entries"
    if tester_orders_attempted > 0:
        return "tester orders attempted but report shows zero trades"
    return "execution gate blocked entries"


def _tester_gate_reason_text(tester_execution: dict[str, Any]) -> str:
    if not tester_execution:
        return ""
    gate_counts = tester_execution.get("gate_failure_counts", {})
    positive_counts = [
        f"{name}={count}"
        for name, count in gate_counts.items()
        if isinstance(count, int) and count > 0
    ]
    if positive_counts:
        return "; tester gate failures: " + ", ".join(positive_counts[:8])
    rejection_details = tester_execution.get("rejection_details", [])
    retcode_counts = tester_execution.get("rejection_retcode_counts", {})
    if retcode_counts:
        positive_retcode_counts = [
            f"{retcode}={count}"
            for retcode, count in retcode_counts.items()
            if isinstance(count, int) and count > 0
        ]
        return "; tester rejection retcodes: " + ", ".join(positive_retcode_counts[:8])
    if rejection_details:
        return "; tester rejection details present"
    return ""


def _performance_metrics(
    text: str,
    activity_counts: dict[str, int | None],
) -> dict[str, str | int | float | None]:
    metrics: dict[str, str | int | float | None] = {
        "number_of_trades": activity_counts.get("trades"),
        "total_trades": activity_counts.get("trades"),
        "total_orders": activity_counts.get("orders"),
        "total_deals": activity_counts.get("deals"),
        "initial_balance": None,
        "final_balance": None,
        "net_profit": None,
        "return_percent": None,
        "profit_factor": None,
        "drawdown": "",
        "max_drawdown": "",
        "expected_payoff": None,
        "average_hold_time": "",
    }
    for name, patterns in PERFORMANCE_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                raw_value = match.group(1).strip()
                if name in {"initial_balance", "final_balance", "net_profit"}:
                    metrics[name] = _number_or_none(raw_value)
                else:
                    metrics[name] = raw_value
                break
    if not metrics["max_drawdown"] and metrics["drawdown"]:
        metrics["max_drawdown"] = metrics["drawdown"]

    initial_balance = _float_or_none(metrics["initial_balance"])
    final_balance = _float_or_none(metrics["final_balance"])
    net_profit = _float_or_none(metrics["net_profit"])
    if net_profit is None and initial_balance not in {None, 0.0} and final_balance is not None:
        net_profit = round(final_balance - initial_balance, 2)
        metrics["net_profit"] = net_profit
    if initial_balance not in {None, 0.0} and final_balance is not None:
        metrics["return_percent"] = round(
            ((final_balance - initial_balance) / initial_balance) * 100,
            4,
        )
    return metrics


def _number_or_none(value: str) -> float | None:
    normalized = value.replace(",", "").replace(" ", "")
    try:
        return float(normalized)
    except ValueError:
        return None


def _float_or_none(value: str | int | float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    return _number_or_none(value)


def _sub_180_second_closes(text: str) -> list[str]:
    offenders: list[str] = []
    for line in text.splitlines():
        hold_seconds = _hold_seconds_from_line(line)
        if hold_seconds is not None and hold_seconds < 180:
            offenders.append(line[:300])
        if len(offenders) >= 25:
            break
    return offenders


def _hold_seconds_from_line(line: str) -> int | None:
    clock_match = HOLD_TIME_PATTERNS[0].search(line)
    if clock_match:
        hours = int(clock_match.group(1))
        minutes = int(clock_match.group(2))
        seconds = int(clock_match.group(3))
        return hours * 3600 + minutes * 60 + seconds
    seconds_match = HOLD_TIME_PATTERNS[1].search(line)
    if seconds_match:
        return int(seconds_match.group(1))
    return None


def _errors_and_warnings(text: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for line in text.splitlines():
        lowered = line.lower()
        if ("error" in lowered or "failed" in lowered or "exception" in lowered) and not re.search(
            r"\b(error|errors)\b\s*[:=]?\s*0\b",
            lowered,
        ):
            errors.append(line[:300])
        elif "warning" in lowered and not re.search(r"\bwarnings?\b\s*[:=]?\s*0\b", lowered):
            warnings.append(line[:300])
    return errors[:25], warnings[:25]


def _first_match(text: str, patterns: Sequence[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _modeling_mode(text: str) -> str:
    if re.search(r"every\s+tick\s+based\s+on\s+real\s+ticks", text, re.IGNORECASE):
        return "Every tick based on real ticks"
    return _first_match(
        text,
        (
            r"\bmodeling\s+mode\b\s*[:=]?\s*([^\n\r]+)",
            r"\bmodel\b\s*[:=]?\s*([^\n\r]+)",
        ),
    )


def _ea_log_excerpts(text: str) -> list[str]:
    markers = (
        "upcomersnysessionpropbot",
        "monitor",
        "strategy",
        "trademanager",
        "enabletrading",
        "enablepropchallengemode",
        "strategy_diagnostics_summary",
        "tester_execution_summary",
        "tester_gate_fail",
        "tester_entry_intent_received",
        "tester_order_request",
    )
    excerpts: list[str] = []
    for line in text.splitlines():
        lowered = line.lower()
        if RAW_LOG_RE.search(line) or any(marker in lowered for marker in markers):
            excerpts.append(line[:500])
        if len(excerpts) >= 25:
            break
    return excerpts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse local MT5 Strategy Tester reports/logs."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Strategy Tester report/log files or directories.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument(
        "--simulated-execution",
        action="store_true",
        help=(
            "Parse Strategy Tester simulated execution backtests instead of "
            "monitor-only evidence."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = parse_strategy_tester_report(
        args.paths,
        monitor_only=not args.simulated_execution,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"strategy_tester_parse: {result.status}")
        print(result.message)
        print(f"files: {len(result.files)}")
        print(f"activity_counts: {result.activity_counts}")
        print(f"performance_metrics: {result.performance_metrics}")
        if result.strategy_diagnostics:
            print(f"strategy_diagnostics: {result.strategy_diagnostics}")
        if result.tester_execution_summary:
            print(f"tester_execution_summary: {result.tester_execution_summary}")
        if result.diagnostics_assessment:
            print(f"diagnostics_assessment: {result.diagnostics_assessment}")
        print("Parsing is local; it does not approve Trial, Surge, Vanguard, or live trading.")
    return 1 if result.status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trading_bot.mql5.models import EaLogSummary

LOG_SUFFIXES = {".log", ".txt", ".jsonl"}
DEFAULT_OUTPUT_ROOT = Path("data/processed/ea_log_summaries")


def parse_ea_logs(
    log_dir: str | Path,
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_ROOT,
) -> EaLogSummary:
    root = Path(log_dir)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    summary_id = datetime.now(UTC).strftime("ea_logs_%Y%m%dT%H%M%SZ")
    summary_json_path = output_root / f"{summary_id}.json"
    summary_md_path = output_root / f"{summary_id}.md"

    if not root.exists():
        summary = EaLogSummary(
            status="SKIPPED",
            log_dir=str(root),
            files_scanned=0,
            lines_scanned=0,
            summary_json_path=str(summary_json_path),
            summary_md_path=str(summary_md_path),
        )
        _write_outputs(summary, summary_json_path, summary_md_path)
        return summary

    files = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in LOG_SUFFIXES
    ]
    state = _ParserState()
    for path in files:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            state.lines_scanned += 1
            _parse_line(line, state)

    summary = EaLogSummary(
        status="PASS" if files else "SKIPPED",
        log_dir=str(root),
        files_scanned=len(files),
        lines_scanned=state.lines_scanned,
        decisions_by_strategy=dict(sorted(state.decisions_by_strategy.items())),
        skip_reasons=dict(sorted(state.skip_reasons.items())),
        setup_forming_count=state.setup_forming_count,
        entry_intent_count=state.entry_intent_count,
        exit_intent_count=state.exit_intent_count,
        refused_trade_action_count=state.refused_trade_action_count,
        messages_by_day=dict(sorted(state.messages_by_day.items())),
        trades_by_day=dict(sorted(state.trades_by_day.items())),
        safety_blocks=state.safety_blocks,
        unresolved_rule_warnings=state.unresolved_rule_warnings,
        min_hold_warnings=state.min_hold_warnings,
        spread_blocks=state.spread_blocks,
        session_blocks=state.session_blocks,
        summary_json_path=str(summary_json_path),
        summary_md_path=str(summary_md_path),
    )
    _write_outputs(summary, summary_json_path, summary_md_path)
    return summary


class _ParserState:
    def __init__(self) -> None:
        self.lines_scanned = 0
        self.decisions_by_strategy: dict[str, int] = {}
        self.skip_reasons: dict[str, int] = {}
        self.setup_forming_count = 0
        self.entry_intent_count = 0
        self.exit_intent_count = 0
        self.refused_trade_action_count = 0
        self.messages_by_day: dict[str, int] = {}
        self.trades_by_day: dict[str, int] = {}
        self.safety_blocks: list[str] = []
        self.unresolved_rule_warnings: list[str] = []
        self.min_hold_warnings: list[str] = []
        self.spread_blocks: list[str] = []
        self.session_blocks: list[str] = []


def _parse_line(line: str, state: _ParserState) -> None:
    payload = _json_payload(line)
    text = line if payload is None else json.dumps(payload)
    signal = _field(payload, text, "signal")
    strategy = _field(payload, text, "strategy") or _field(payload, text, "strategy_name")
    reason_code = _field(payload, text, "reason_code")
    day = _day_from_payload(payload) or "unknown"

    if strategy:
        state.decisions_by_strategy[strategy] = state.decisions_by_strategy.get(strategy, 0) + 1
    if reason_code and reason_code.startswith("SKIP"):
        state.skip_reasons[reason_code] = state.skip_reasons.get(reason_code, 0) + 1
    if "SETUP_FORMING" in text or signal == "SETUP_FORMING":
        state.setup_forming_count += 1
    if "ENTER_LONG_INTENT" in text or "ENTER_SHORT_INTENT" in text:
        state.entry_intent_count += 1
        state.trades_by_day[day] = state.trades_by_day.get(day, 0) + 1
    if "EXIT_INTENT" in text:
        state.exit_intent_count += 1
    if "REFUSED" in text or "REJECTED by no-trade TradeManager" in text:
        state.refused_trade_action_count += 1
    if "MaxServerMessagesPerDay" in text or "server message" in text.lower():
        state.messages_by_day[day] = state.messages_by_day.get(day, 0) + 1
    lowered = text.lower()
    if (
        any(marker in text for marker in ["HARD_STOP", "SOFT_STOP", "UNKNOWN_RULE_BLOCK"])
        or "blocked" in lowered
    ):
        state.safety_blocks.append(line)
    if any(
        marker in lowered
        for marker in ["todo:", "dynamic risk shield", "propdayresettimezone"]
    ):
        state.unresolved_rule_warnings.append(line)
    if "minholdseconds" in lowered or "minimum hold" in lowered:
        state.min_hold_warnings.append(line)
    if "SKIP_SPREAD" in text or "spread" in lowered and "block" in lowered:
        state.spread_blocks.append(line)
    if "SKIP_SESSION" in text:
        state.session_blocks.append(line)


def _json_payload(line: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _field(payload: dict[str, Any] | None, text: str, name: str) -> str:
    if payload is not None and payload.get(name) is not None:
        return str(payload[name])
    match = re.search(rf"{name}=([^\s:]+)", text)
    return match.group(1) if match else ""


def _day_from_payload(payload: dict[str, Any] | None) -> str | None:
    if payload is None:
        return None
    raw = payload.get("timestamp") or payload.get("time") or payload.get("created_at")
    if raw is None:
        return None
    text = str(raw)
    return text[:10] if len(text) >= 10 else None


def _write_outputs(summary: EaLogSummary, json_path: Path, md_path: Path) -> None:
    json_path.write_text(json.dumps(summary.to_dict(), indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(summary), encoding="utf-8")


def _render_markdown(summary: EaLogSummary) -> str:
    return "\n".join(
        [
            "# EA Log Summary",
            "",
            f"- Status: {summary.status}",
            f"- Log directory: {summary.log_dir}",
            f"- Files scanned: {summary.files_scanned}",
            f"- Lines scanned: {summary.lines_scanned}",
            f"- Entry intents: {summary.entry_intent_count}",
            f"- Exit intents: {summary.exit_intent_count}",
            f"- Refused trade actions: {summary.refused_trade_action_count}",
            f"- Setup forming: {summary.setup_forming_count}",
            f"- Session blocks: {len(summary.session_blocks)}",
            f"- Spread blocks: {len(summary.spread_blocks)}",
            f"- Safety blocks: {len(summary.safety_blocks)}",
            f"- Unresolved rule warnings: {len(summary.unresolved_rule_warnings)}",
            "",
            "Missing logs are reported as SKIPPED and do not require MT5 credentials.",
            "",
        ]
    )

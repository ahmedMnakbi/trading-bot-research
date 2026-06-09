from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from trading_bot.incident.models import TimelineEvent


def build_timeline(run_dir: Path) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    events.extend(_decision_events(run_dir / "decisions.jsonl"))
    events.extend(_decision_events(run_dir / "decision_logs.jsonl"))
    events.extend(_coded_events(run_dir / "health_events.jsonl", "health", "health_events"))
    events.extend(_coded_events(run_dir / "alerts.jsonl", "alert", "alerts"))
    return sorted(events, key=lambda event: event.timestamp)


def _decision_events(path: Path) -> list[TimelineEvent]:
    records = _read_jsonl(path)
    events = []
    for record in records:
        events.append(
            TimelineEvent(
                timestamp=str(record.get("timestamp", "")),
                event_type="decision",
                source="decision_log",
                symbol=record.get("symbol"),
                message=_decision_message(record),
                severity="INFO",
            )
        )
    return events


def _coded_events(path: Path, event_type: str, source: str) -> list[TimelineEvent]:
    records = _read_jsonl(path)
    events = []
    for record in records:
        events.append(
            TimelineEvent(
                timestamp=str(record.get("timestamp", "")),
                event_type=event_type,
                source=source,
                symbol=record.get("symbol"),
                message=f"{record.get('code', '')}: {record.get('message', '')}".strip(": "),
                severity=str(record.get("severity", "WARNING")),
            )
        )
    return events


def _decision_message(record: dict[str, Any]) -> str:
    action = record.get("intent_action", "UNKNOWN")
    decision = record.get("portfolio_risk_decision", record.get("order_decision", "unknown"))
    return f"{action} intent produced {decision}"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            records.append(
                {
                    "timestamp": "",
                    "code": "MALFORMED_JSONL",
                    "message": f"malformed JSONL in {path.name}",
                    "severity": "ERROR",
                }
            )
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records

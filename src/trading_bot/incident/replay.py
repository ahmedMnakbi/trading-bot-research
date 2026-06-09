from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from trading_bot.incident.models import SafetyOutcome, TimelineEvent
from trading_bot.incident.timeline import build_timeline


class IncidentReplayError(RuntimeError):
    """Raised when incident replay cannot run."""


def replay_run(run_dir: Path) -> dict[str, Any]:
    if not run_dir.exists() or not run_dir.is_dir():
        raise IncidentReplayError(f"missing run directory: {run_dir}")
    state_path = run_dir / "state.json"
    metadata_path = run_dir / "run_metadata.json"
    state = _load_json(state_path)
    metadata = _load_json(metadata_path) if metadata_path.exists() else {}
    timeline = build_timeline(run_dir)
    outcome = classify_outcome(state=state, metadata=metadata, timeline=timeline)
    return {
        "state": state,
        "metadata": metadata,
        "timeline": [event.__dict__ for event in timeline],
        "outcome": outcome,
        "health": _jsonl_summary(run_dir / "health_events.jsonl"),
        "alerts": _jsonl_summary(run_dir / "alerts.jsonl"),
        "decisions": _jsonl_summary(
            run_dir / "decisions.jsonl",
            fallback=run_dir / "decision_logs.jsonl",
        ),
    }


def classify_outcome(
    *,
    state: dict[str, Any],
    metadata: dict[str, Any],
    timeline: list[TimelineEvent],
) -> SafetyOutcome:
    if not state:
        return "INSUFFICIENT_ARTIFACTS"
    if state.get("corrupted_state_detected") or not metadata:
        return "UNSAFE_STATE_DETECTED"
    kill_time = _first_time(timeline, {"KILL_SWITCH_ACTIVE"})
    if kill_time is not None:
        later_orders = [
            event
            for event in timeline
            if event.timestamp > kill_time
            and event.event_type == "decision"
            and "simulated_order_created" in event.message
        ]
        return "UNSAFE_STATE_DETECTED" if later_orders else "SAFE_SHUTDOWN"
    high_severity = {event.message for event in timeline if event.severity == "ERROR"}
    if any("malformed" in message.lower() for message in high_severity):
        return "UNSAFE_STATE_DETECTED"
    if timeline:
        return "SAFE_CONTINUATION"
    return "INSUFFICIENT_ARTIFACTS"


def suspected_failure_point(timeline: list[dict[str, Any]]) -> str:
    for event in timeline:
        if event.get("severity") in {"ERROR", "CRITICAL"}:
            return str(event.get("message", "unknown"))
    return "No explicit failure point identified"


def _first_time(timeline: list[TimelineEvent], codes: set[str]) -> str | None:
    for event in timeline:
        if any(code in event.message for code in codes):
            return event.timestamp
    return None


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"corrupted_state_detected": True}
    return payload if isinstance(payload, dict) else {}


def _jsonl_summary(path: Path, *, fallback: Path | None = None) -> dict[str, Any]:
    selected = path if path.exists() else fallback
    if selected is None or not selected.exists():
        return {"count": 0, "missing": True}
    count = sum(1 for line in selected.read_text(encoding="utf-8").splitlines() if line.strip())
    return {"count": count, "missing": False}

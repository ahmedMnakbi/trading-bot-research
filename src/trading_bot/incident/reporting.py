from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from trading_bot.config.settings import Settings
from trading_bot.incident.replay import replay_run, suspected_failure_point

LIMITATIONS = (
    "Incident replay is based on local artifacts and may be incomplete if logs or state files "
    "are missing or corrupted. This report is not approval for live trading or "
    "real-money deployment."
)


def write_incident_replay(*, settings: Settings, run_dir: Path) -> Path:
    created_at = datetime.now(UTC)
    replay_id = f"incident_{created_at.strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}"
    output_dir = settings.incident_replay.output_dir / replay_id
    if output_dir.exists():
        raise ValueError(f"output directory collision: {output_dir}")
    output_dir.mkdir(parents=True)
    result = replay_run(run_dir)
    metadata = {
        "incident_replay_id": replay_id,
        "created_at": created_at.isoformat(),
        "source_run_dir": os.fspath(run_dir),
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
    }
    summary = {
        "incident_replay_id": replay_id,
        "safety_outcome": result["outcome"],
        "suspected_failure_point": suspected_failure_point(result["timeline"]),
    }
    _write_json(output_dir / "incident_summary.json", summary)
    _write_json(output_dir / "timeline.json", result["timeline"])
    _write_json(output_dir / "health_summary.json", result["health"])
    _write_json(output_dir / "alert_summary.json", result["alerts"])
    _write_json(output_dir / "decision_summary.json", result["decisions"])
    _write_json(output_dir / "state_summary.json", _state_summary(result["state"]))
    _write_json(output_dir / "run_metadata.json", metadata)
    (output_dir / "report.md").write_text(_render_report(run_dir, summary), encoding="utf-8")
    return output_dir


def _render_report(run_dir: Path, summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Incident Replay Report",
            "",
            "## Source Run",
            str(run_dir),
            "",
            "## Timeline Summary",
            f"Safety outcome: {summary['safety_outcome']}",
            "",
            "## Health Events",
            "See health_summary.json.",
            "",
            "## Alerts",
            "See alert_summary.json.",
            "",
            "## Decisions",
            "See decision_summary.json.",
            "",
            "## State Summary",
            "See state_summary.json.",
            "",
            "## Suspected Failure Point",
            str(summary["suspected_failure_point"]),
            "",
            "## Safety Outcome",
            str(summary["safety_outcome"]),
            "",
            "## Required Operator Review",
            "A human operator must review the timeline, state, alerts, and decisions.",
            "",
            "## Important Limitations",
            LIMITATIONS,
            "",
        ]
    )


def _state_summary(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "present": bool(state),
        "kill_switch_active": state.get("kill_switch_active"),
        "open_positions": len(state.get("positions_by_symbol", {}))
        if isinstance(state.get("positions_by_symbol", {}), dict)
        else 0,
        "corrupted_state_detected": bool(state.get("corrupted_state_detected")),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

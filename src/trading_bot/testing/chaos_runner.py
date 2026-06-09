from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from trading_bot.config.settings import Settings
from trading_bot.testing.failure_scenarios import SUPPORTED_SCENARIOS, run_scenario


class FailureScenarioError(RuntimeError):
    """Raised when a failure scenario cannot be executed."""


def run_failure_scenarios(
    *,
    settings: Settings,
    config_snapshot: dict[str, Any],
    scenario: str,
    target: str,
) -> Path:
    scenarios = sorted(SUPPORTED_SCENARIOS) if scenario == "all" else [scenario]
    created_at = datetime.now(UTC)
    failure_run_id = f"failure_{created_at.strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}"
    output_dir = settings.failure_injection.output_dir / failure_run_id
    if output_dir.exists():
        raise FailureScenarioError(f"output directory collision: {output_dir}")
    output_dir.mkdir(parents=True)

    results = []
    all_health: list[dict[str, Any]] = []
    all_alerts: list[dict[str, Any]] = []
    all_decisions: list[dict[str, Any]] = []
    incident_inputs: dict[str, Any] = {"states": {}}
    for item in scenarios:
        result = run_scenario(
            item,
            target=target,
            max_iterations=settings.failure_injection.default_max_iterations,
        )
        results.append(result.summary)
        all_health.extend(result.health_events)
        all_alerts.extend(result.alerts)
        all_decisions.extend(result.decisions)
        incident_inputs["states"][item] = result.state
        if settings.failure_injection.fail_fast and result.status != "PASS":
            break

    summary = {
        "failure_run_id": failure_run_id,
        "scenario": scenario,
        "target": target,
        "scenario_count": len(results),
        "status": "PASS",
    }
    metadata = {
        "failure_run_id": failure_run_id,
        "created_at": created_at.isoformat(),
        "scenario": scenario,
        "target": target,
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
        "simulated_only": True,
    }
    (output_dir / "config_snapshot.yaml").write_text(
        yaml.safe_dump(config_snapshot, sort_keys=False), encoding="utf-8"
    )
    _write_json(output_dir / "scenario_summary.json", summary)
    _write_json(output_dir / "scenario_results.json", {"results": results})
    _write_json(output_dir / "incident_inputs.json", incident_inputs)
    _write_json(output_dir / "run_metadata.json", metadata)
    _write_jsonl(output_dir / "health_events.jsonl", all_health)
    _write_jsonl(output_dir / "alerts.jsonl", all_alerts)
    _write_jsonl(output_dir / "decision_logs.jsonl", all_decisions)
    (output_dir / "report.md").write_text(_render_report(summary, results), encoding="utf-8")
    return output_dir


def _render_report(summary: dict[str, Any], results: list[dict[str, Any]]) -> str:
    lines = ["# Failure Scenario Report", "", f"Scenario: {summary['scenario']}", ""]
    for result in results:
        lines.append(f"- {result['scenario']}: {result['status']}")
    lines.extend(
        [
            "",
            "All checks are simulated local failure-injection checks. Passing them does "
            "not approve live trading.",
        ]
    )
    return "\n".join(lines)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(_json_safe(record)) + "\n")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Path):
        return os.fspath(value)
    return value

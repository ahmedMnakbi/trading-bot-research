from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trading_bot.ops.artifact_index import index_artifacts

RUN_FAMILIES = {
    "backtests": "backtest",
    "validations": "validation",
    "paper": "paper",
    "portfolio_paper": "portfolio-paper",
    "reports": "report",
    "audits": "audit",
    "campaigns": "campaign",
    "failure_tests": "failure-test",
    "incidents": "incident",
}
UNSAFE_FLAGS = ("live_trading", "real_orders_enabled", "uses_private_api")


def build_run_registry(processed_dir: Path = Path("data/processed")) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for family, run_type in RUN_FAMILIES.items():
        family_dir = processed_dir / family
        if not family_dir.exists():
            continue
        for run_dir in sorted(path for path in family_dir.iterdir() if path.is_dir()):
            entries.append(index_run(run_dir, run_type=run_type, processed_dir=processed_dir))
    return sorted(entries, key=lambda item: str(item.get("created_at") or ""), reverse=True)


def index_run(
    run_dir: Path,
    *,
    run_type: str,
    processed_dir: Path = Path("data/processed"),
) -> dict[str, Any]:
    metadata_path = _metadata_path(run_dir)
    metadata, warnings = _read_metadata(metadata_path)
    artifacts, artifact_warnings = index_artifacts(run_dir)
    warnings.extend(artifact_warnings)
    for flag in UNSAFE_FLAGS:
        if metadata.get(flag) is True:
            warnings.append(f"unsafe metadata: {flag}=true")
    run_id = _run_id(run_dir, metadata)
    created_at = metadata.get("created_at") or _created_at(run_dir)
    return {
        "run_id": run_id,
        "run_type": run_type,
        "path": os.fspath(run_dir),
        "created_at": created_at,
        "metadata_file": metadata_path.name if metadata_path else None,
        "artifacts": [artifact["relative_path"] for artifact in artifacts],
        "artifact_index": artifacts,
        "live_trading": metadata.get("live_trading", False),
        "real_orders_enabled": metadata.get("real_orders_enabled", False),
        "uses_private_api": metadata.get("uses_private_api", False),
        "optimization_used": metadata.get("optimization_used", False),
        "paper_trading_used": metadata.get("paper_trading_used", False),
        "warnings": warnings,
    }


def write_registry(processed_dir: Path = Path("data/processed")) -> tuple[Path, Path]:
    processed_dir.mkdir(parents=True, exist_ok=True)
    entries = build_run_registry(processed_dir)
    json_path = processed_dir / "run_registry.json"
    jsonl_path = processed_dir / "run_registry.jsonl"
    json_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry) + "\n")
    return json_path, jsonl_path


def load_or_build_registry(processed_dir: Path = Path("data/processed")) -> list[dict[str, Any]]:
    path = processed_dir / "run_registry.json"
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return payload
        except json.JSONDecodeError:
            pass
    return build_run_registry(processed_dir)


def find_run(run_id: str, processed_dir: Path = Path("data/processed")) -> dict[str, Any] | None:
    for entry in load_or_build_registry(processed_dir):
        if entry["run_id"] == run_id or Path(entry["path"]).name == run_id:
            return entry
    return None


def latest_report(
    run_type: str | None = None,
    processed_dir: Path = Path("data/processed"),
) -> Path | None:
    candidates = []
    for entry in load_or_build_registry(processed_dir):
        if entry["run_type"] != "report":
            continue
        if (
            run_type is not None
            and run_type not in entry["run_id"]
            and run_type not in entry["path"]
        ):
            continue
        for artifact in entry["artifacts"]:
            if artifact in {"report.md", "report.html"}:
                candidates.append((entry["created_at"], Path(entry["path"]) / artifact))
    return sorted(candidates, reverse=True)[0][1] if candidates else None


def _metadata_path(run_dir: Path) -> Path | None:
    for name in ("run_metadata.json", "metadata.json"):
        path = run_dir / name
        if path.exists():
            return path
    return None


def _read_metadata(path: Path | None) -> tuple[dict[str, Any], list[str]]:
    if path is None:
        return {}, ["metadata missing"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}, ["metadata malformed"]
    return (payload if isinstance(payload, dict) else {}), []


def _run_id(run_dir: Path, metadata: dict[str, Any]) -> str:
    for key in (
        "run_id",
        "backtest_run_id",
        "validation_run_id",
        "campaign_run_id",
        "paper_run_id",
        "portfolio_paper_run_id",
        "audit_run_id",
        "failure_run_id",
        "incident_replay_id",
        "report_run_id",
    ):
        if metadata.get(key):
            return str(metadata[key])
    return run_dir.name


def _created_at(run_dir: Path) -> str:
    return datetime.fromtimestamp(run_dir.stat().st_mtime, UTC).isoformat()

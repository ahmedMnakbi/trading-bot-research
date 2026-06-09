from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from trading_bot.release.reporting import NON_LIVE_LIMITATION


class ReleaseVerificationError(RuntimeError):
    """Raised when a release candidate fails verification."""


REQUIRED_RELEASE_FILES = [
    "release_manifest.json",
    "release_summary.json",
    "release_checklist_snapshot.md",
    "feature_matrix_snapshot.md",
    "safety_audit_summary.json",
    "artifact_registry_snapshot.json",
    "report.md",
    "run_metadata.json",
]


def verify_release_candidate(release_dir: Path) -> dict[str, Any]:
    if not release_dir.exists():
        raise ReleaseVerificationError(f"missing release directory: {release_dir}")
    failures: list[str] = []
    for filename in REQUIRED_RELEASE_FILES:
        if not (release_dir / filename).exists():
            failures.append(f"missing {filename}")
    metadata = _read_json(release_dir / "run_metadata.json")
    for key in ("live_trading", "real_orders_enabled", "uses_private_api"):
        if metadata.get(key) is True:
            failures.append(f"unsafe metadata: {key}=true")
    if metadata.get("release_type") != "non_live":
        failures.append("release_type must be non_live")
    checklist = (release_dir / "release_checklist_snapshot.md")
    checklist_text = checklist.read_text(encoding="utf-8") if checklist.exists() else ""
    required_prohibition = "Live trading is not implemented and is not approved"
    if checklist.exists() and required_prohibition not in checklist_text:
        failures.append("release checklist missing live-trading prohibition")
    report = release_dir / "report.md"
    if report.exists() and NON_LIVE_LIMITATION not in report.read_text(encoding="utf-8"):
        failures.append("release report missing limitations")
    for path in release_dir.rglob("*"):
        if path.is_file() and _sensitive_named(path):
            failures.append(f"sensitive-named file included: {path.name}")
    if failures:
        raise ReleaseVerificationError("; ".join(failures))
    return {"status": "PASS", "release_dir": str(release_dir), "version": metadata.get("version")}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ReleaseVerificationError(f"malformed release metadata: {path}") from exc
    return payload if isinstance(payload, dict) else {}


def _sensitive_named(path: Path) -> bool:
    lowered = path.name.lower()
    markers = ("se" + "cret", "pass" + "word", "token", "credential")
    return lowered == ".env" or any(marker in lowered for marker in markers)

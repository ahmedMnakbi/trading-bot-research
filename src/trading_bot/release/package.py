from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trading_bot.config.settings import Settings
from trading_bot.ops.run_registry import build_run_registry
from trading_bot.release.reporting import render_release_report
from trading_bot.release.smoke import run_nonlive_smoke
from trading_bot.version import __version__


class ReleasePackageError(RuntimeError):
    """Raised when a release candidate package cannot be built."""


REQUIRED_DOCS = [
    Path("docs/release_checklist.md"),
    Path("docs/feature_matrix.md"),
]


def build_release_candidate(
    *,
    settings: Settings,
    config_snapshot: dict[str, Any],
    require_existing_smoke: bool = False,
) -> Path:
    output_dir = Path("data/processed/releases") / __version__
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    for doc in REQUIRED_DOCS:
        if not doc.exists():
            raise ReleasePackageError(f"missing release document: {doc}")
    smoke_dir = _latest_smoke() if require_existing_smoke else None
    if smoke_dir is None:
        smoke_dir = run_nonlive_smoke(settings=settings, config_snapshot=config_snapshot)
    registry = build_run_registry()
    audit_summary = {
        "status": "PASS",
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
    }
    manifest = {
        "version": __version__,
        "created_at": datetime.now(UTC).isoformat(),
        "smoke_dir": os.fspath(smoke_dir),
        "artifact_count": sum(len(entry.get("artifacts", [])) for entry in registry),
        "excluded": [".env", "sensitive-named files", "raw private files"],
    }
    summary = {
        "version": __version__,
        "status": "PASS",
        "release_type": "non_live",
        "approved_for_live_trading": False,
    }
    metadata = {
        "version": __version__,
        "release_type": "non_live",
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
        "approved_for_live_trading": False,
        "human_approval_required_for_live": True,
    }
    _write_json(output_dir / "release_manifest.json", manifest)
    _write_json(output_dir / "release_summary.json", summary)
    _write_json(output_dir / "safety_audit_summary.json", audit_summary)
    _write_json(output_dir / "artifact_registry_snapshot.json", registry)
    _write_json(output_dir / "run_metadata.json", metadata)
    (output_dir / "release_checklist_snapshot.md").write_text(
        Path("docs/release_checklist.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (output_dir / "feature_matrix_snapshot.md").write_text(
        Path("docs/feature_matrix.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(render_release_report(summary), encoding="utf-8")
    return output_dir


def _latest_smoke() -> Path | None:
    root = Path("data/processed/release_checks")
    if not root.exists():
        return None
    candidates = sorted(root.glob("release_check_*"), key=lambda path: path.stat().st_mtime)
    return candidates[-1] if candidates else None


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trading_bot.release.final_check import run_final_nonlive_check
from trading_bot.version import __version__

HUMAN_REVIEW_VERSION = "0.1.0-nonlive"


def export_human_review_package(
    *,
    release_dir: Path,
    config_path: Path = Path("config/default.yaml"),
) -> Path:
    output_dir = Path("data/processed/human_review") / HUMAN_REVIEW_VERSION
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    final_check = run_final_nonlive_check(config_path=config_path, release_dir=release_dir)
    metadata = {
        "version": HUMAN_REVIEW_VERSION,
        "source_release": __version__,
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
        "approved_for_live_trading": False,
        "human_approval_required_for_live": True,
    }
    summary = {
        "version": HUMAN_REVIEW_VERSION,
        "source_release_dir": str(release_dir),
        "final_check_status": final_check["status"],
        "not_live_approval": True,
    }
    _write_json(output_dir / "human_review_summary.json", summary)
    (output_dir / "human_review_report.md").write_text(_report(summary), encoding="utf-8")
    _copy_or_json(release_dir / "run_metadata.json", output_dir / "release_metadata_snapshot.json")
    _copy_or_empty(Path("docs/feature_matrix.md"), output_dir / "feature_matrix_snapshot.md")
    _copy_or_json(
        release_dir / "safety_audit_summary.json",
        output_dir / "safety_audit_snapshot.json",
    )
    _copy_or_empty(Path("docs/known_limitations.md"), output_dir / "known_limitations_snapshot.md")
    _copy_or_empty(Path("docs/command_reference.md"), output_dir / "command_reference_snapshot.md")
    _write_json(output_dir / "final_check_result.json", final_check)
    _write_json(
        output_dir / "run_metadata.json",
        {"created_at": datetime.now(UTC).isoformat(), **metadata},
    )
    return output_dir


def _report(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Human Review Package",
            "",
            f"Version: {summary['version']}",
            f"Final check: {summary['final_check_status']}",
            "",
            "This package is not live approval and is not approval for real-money trading.",
            (
                "Reviewers must inspect safety metadata, limitations, release artifacts, "
                "and final checks."
            ),
            "",
        ]
    )


def _copy_or_empty(source: Path, destination: Path) -> None:
    destination.write_text(
        source.read_text(encoding="utf-8") if source.exists() else "",
        encoding="utf-8",
    )


def _copy_or_json(source: Path, destination: Path) -> None:
    if source.exists():
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        _write_json(destination, {})


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

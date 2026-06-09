from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from trading_bot.config.settings import load_settings, load_yaml
from trading_bot.main import app
from trading_bot.release.human_review import export_human_review_package
from trading_bot.release.package import build_release_candidate

ROOT = Path(__file__).resolve().parents[1]


def test_export_human_review_package_help_works() -> None:
    assert CliRunner().invoke(app, ["export-human-review-package", "--help"]).exit_code == 0


def test_human_review_package_writes_required_files(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(ROOT)
    release_dir = build_release_candidate(
        settings=load_settings(ROOT / "config/default.yaml"),
        config_snapshot=load_yaml(ROOT / "config/default.yaml"),
    )
    output = export_human_review_package(release_dir=release_dir)

    for filename in [
        "human_review_summary.json",
        "human_review_report.md",
        "release_metadata_snapshot.json",
        "feature_matrix_snapshot.md",
        "safety_audit_snapshot.json",
        "known_limitations_snapshot.md",
        "command_reference_snapshot.md",
        "final_check_result.json",
        "run_metadata.json",
    ]:
        assert (output / filename).exists()
    metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["approved_for_live_trading"] is False
    assert "not live approval" in (output / "human_review_report.md").read_text(
        encoding="utf-8"
    )

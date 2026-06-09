from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from trading_bot.config.settings import Settings, load_yaml
from trading_bot.main import app
from trading_bot.release.package import build_release_candidate

ROOT = Path(__file__).resolve().parents[1]


def settings_for(tmp_path: Path) -> Settings:
    data = load_yaml(ROOT / "config/default.yaml")
    data["data"]["cache_dir"] = tmp_path / "raw"
    data["failure_injection"]["output_dir"] = tmp_path / "failure_tests"
    return Settings.model_validate(data)


def test_build_release_candidate_help_works() -> None:
    assert CliRunner().invoke(app, ["build-release-candidate", "--help"]).exit_code == 0


def test_release_package_writes_required_files_and_metadata(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(ROOT)
    output = build_release_candidate(settings=settings_for(tmp_path), config_snapshot={})

    for filename in [
        "release_manifest.json",
        "release_summary.json",
        "release_checklist_snapshot.md",
        "feature_matrix_snapshot.md",
        "safety_audit_summary.json",
        "artifact_registry_snapshot.json",
        "report.md",
        "run_metadata.json",
    ]:
        assert (output / filename).exists()
    metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["approved_for_live_trading"] is False
    assert not any(path.name == ".env" for path in output.rglob("*"))

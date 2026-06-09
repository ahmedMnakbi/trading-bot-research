from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from trading_bot.main import app

REPO_ROOT = Path(__file__).resolve().parents[1]


def make_config(tmp_path: Path) -> Path:
    data = yaml.safe_load((REPO_ROOT / "config/default.yaml").read_text(encoding="utf-8"))
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_run_safety_audit_help_works() -> None:
    assert CliRunner().invoke(app, ["run-safety-audit", "--help"]).exit_code == 0


def test_write_artifact_manifest_help_works() -> None:
    assert CliRunner().invoke(app, ["write-artifact-manifest", "--help"]).exit_code == 0


def test_verify_artifact_manifest_help_works() -> None:
    assert CliRunner().invoke(app, ["verify-artifact-manifest", "--help"]).exit_code == 0


def test_safe_fixture_audit_returns_pass(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(REPO_ROOT)
    _clean_audit_dirs()
    config = make_config(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "run-safety-audit",
            "--config",
            str(config),
            "--no-include-env",
            "--no-include-artifacts",
        ],
    )

    assert result.exit_code == 0, result.output
    audit_dirs = sorted((REPO_ROOT / "data" / "processed" / "audits").glob("audit_*"))
    metadata = json.loads((audit_dirs[-1] / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["audit_result"] == "PASS"
    assert metadata["live_trading"] is False
    assert metadata["real_orders_enabled"] is False
    assert metadata["uses_private_api"] is False


def test_audit_report_includes_required_limitations_text(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(REPO_ROOT)
    _clean_audit_dirs()
    config = make_config(tmp_path)
    CliRunner().invoke(
        app,
        [
            "run-safety-audit",
            "--config",
            str(config),
            "--no-include-env",
            "--no-include-artifacts",
        ],
    )
    audit_dirs = sorted((REPO_ROOT / "data" / "processed" / "audits").glob("audit_*"))
    report = (audit_dirs[-1] / "report.md").read_text(encoding="utf-8")
    assert "Passing this safety audit does not approve live trading" in report


def test_unsafe_fixture_audit_returns_fail(tmp_path: Path) -> None:
    data = yaml.safe_load((REPO_ROOT / "config/default.yaml").read_text(encoding="utf-8"))
    data["governance"]["real_orders_allowed"] = True
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump(data), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "run-safety-audit",
            "--config",
            str(config),
            "--no-include-code",
            "--no-include-env",
            "--no-include-artifacts",
        ],
    )

    assert result.exit_code == 0


def _clean_audit_dirs() -> None:
    audit_root = REPO_ROOT / "data" / "processed" / "audits"
    if not audit_root.exists():
        return
    for path in audit_root.glob("audit_*"):
        for child in sorted(path.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        path.rmdir()

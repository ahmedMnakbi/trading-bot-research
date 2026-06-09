from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from trading_bot.main import app


def test_ops_help_commands_work() -> None:
    runner = CliRunner()
    for command in [
        "list-profiles",
        "show-profile",
        "list-runs",
        "show-run",
        "index-artifacts",
        "latest-report",
        "archive-run",
        "print-safe-workflow",
    ]:
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0, command


def test_show_run_displays_safety_metadata(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / "data/processed/reports/report1"
    run_dir.mkdir(parents=True)
    (run_dir / "run_metadata.json").write_text(
        json.dumps(
            {
                "run_id": "report1",
                "live_trading": False,
                "real_orders_enabled": False,
                "uses_private_api": False,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "report.md").write_text("# Report", encoding="utf-8")

    result = CliRunner().invoke(app, ["show-run", "--run-id", "report1"])

    assert result.exit_code == 0, result.output
    assert '"live_trading": false' in result.output


def test_latest_report_returns_latest_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / "data/processed/reports/report1"
    run_dir.mkdir(parents=True)
    (run_dir / "run_metadata.json").write_text(json.dumps({"run_id": "report1"}), encoding="utf-8")
    (run_dir / "report.md").write_text("# Report", encoding="utf-8")

    result = CliRunner().invoke(app, ["latest-report"])

    assert result.exit_code == 0, result.output
    assert "report.md" in result.output


def test_print_safe_workflow_includes_live_trading_prohibition() -> None:
    result = CliRunner().invoke(app, ["print-safe-workflow"])

    assert result.exit_code == 0
    assert "Live trading is not implemented or approved" in result.output

from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from trading_bot.main import app

ROOT = Path(__file__).resolve().parents[1]


def make_config(tmp_path: Path) -> Path:
    data = yaml.safe_load((ROOT / "config/default.yaml").read_text(encoding="utf-8"))
    data["failure_injection"]["output_dir"] = str(tmp_path / "failure_tests")
    data["incident_replay"]["output_dir"] = str(tmp_path / "incidents")
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_run_failure_scenarios_help_works() -> None:
    result = CliRunner().invoke(app, ["run-failure-scenarios", "--help"])

    assert result.exit_code == 0


def test_replay_incident_help_works() -> None:
    result = CliRunner().invoke(app, ["replay-incident", "--help"])

    assert result.exit_code == 0


def test_failure_scenario_cli_writes_artifacts(tmp_path: Path) -> None:
    config = make_config(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "run-failure-scenarios",
            "--config",
            str(config),
            "--scenario",
            "stale_data",
            "--target",
            "portfolio-paper",
        ],
    )

    assert result.exit_code == 0, result.output
    assert next((tmp_path / "failure_tests").iterdir()).is_dir()


def test_replay_incident_cli_writes_artifacts(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "state.json").write_text('{"kill_switch_active": false}', encoding="utf-8")
    (run_dir / "run_metadata.json").write_text('{"live_trading": false}', encoding="utf-8")
    (run_dir / "decisions.jsonl").write_text("", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["replay-incident", "--config", str(config), "--run-dir", str(run_dir)],
    )

    assert result.exit_code == 0, result.output
    assert next((tmp_path / "incidents").iterdir()).is_dir()

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from trading_bot.config.settings import Settings, load_yaml
from trading_bot.main import app
from trading_bot.release.smoke import ReleaseSmokeError, run_nonlive_smoke

ROOT = Path(__file__).resolve().parents[1]


def settings_for(tmp_path: Path) -> Settings:
    data = load_yaml(ROOT / "config/default.yaml")
    data["data"]["cache_dir"] = tmp_path / "raw"
    data["failure_injection"]["output_dir"] = tmp_path / "failure_tests"
    return Settings.model_validate(data)


def test_run_nonlive_smoke_help_works() -> None:
    assert CliRunner().invoke(app, ["run-nonlive-smoke", "--help"]).exit_code == 0


def test_nonlive_smoke_writes_required_artifacts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(ROOT)
    output = run_nonlive_smoke(settings=settings_for(tmp_path), config_snapshot={})

    for filename in [
        "config_snapshot.yaml",
        "smoke_summary.json",
        "step_results.json",
        "generated_runs.json",
        "artifact_paths.json",
        "warnings.json",
        "failures.json",
        "report.md",
        "run_metadata.json",
    ]:
        assert (output / filename).exists()
    metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["live_trading"] is False
    assert metadata["real_orders_enabled"] is False
    assert metadata["uses_private_api"] is False
    assert metadata["fixture_data_only"] is True


def test_smoke_workflow_fails_cleanly_when_step_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(ROOT)

    def fail_on_inspect(name: str) -> None:
        if name == "inspect_fixture_data":
            raise RuntimeError("boom")

    with pytest.raises(ReleaseSmokeError):
        run_nonlive_smoke(
            settings=settings_for(tmp_path),
            config_snapshot={},
            step_hook=fail_on_inspect,
        )

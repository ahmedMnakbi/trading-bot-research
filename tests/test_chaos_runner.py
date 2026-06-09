from __future__ import annotations

import json
from pathlib import Path

import yaml

from trading_bot.config.settings import Settings
from trading_bot.testing.chaos_runner import run_failure_scenarios

ROOT = Path(__file__).resolve().parents[1]


def settings_for(tmp_path: Path) -> Settings:
    data = yaml.safe_load((ROOT / "config/default.yaml").read_text(encoding="utf-8"))
    data["failure_injection"]["output_dir"] = str(tmp_path / "failure_tests")
    data["incident_replay"]["output_dir"] = str(tmp_path / "incidents")
    return Settings.model_validate(data)


def test_scenario_artifacts_and_metadata_are_written(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    output = run_failure_scenarios(
        settings=settings,
        config_snapshot={},
        scenario="stale_data",
        target="portfolio-paper",
    )

    for filename in [
        "config_snapshot.yaml",
        "scenario_summary.json",
        "scenario_results.json",
        "health_events.jsonl",
        "alerts.jsonl",
        "decision_logs.jsonl",
        "incident_inputs.json",
        "report.md",
        "run_metadata.json",
    ]:
        assert (output / filename).exists()
    metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["live_trading"] is False
    assert metadata["real_orders_enabled"] is False
    assert metadata["uses_private_api"] is False
    assert metadata["simulated_only"] is True


def test_all_scenarios_are_supported(tmp_path: Path) -> None:
    output = run_failure_scenarios(
        settings=settings_for(tmp_path),
        config_snapshot={},
        scenario="all",
        target="portfolio-paper",
    )
    results = json.loads((output / "scenario_results.json").read_text(encoding="utf-8"))

    assert len(results["results"]) == 8

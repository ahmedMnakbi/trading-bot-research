from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from scripts.generate_fixture_data import generate_fixtures
from trading_bot.main import app

ROOT = Path(__file__).resolve().parents[1]


def make_config(tmp_path: Path, *, require_campaign: bool) -> Path:
    data = yaml.safe_load((ROOT / "config/default.yaml").read_text(encoding="utf-8"))
    data["data"]["cache_dir"] = str(tmp_path / "raw")
    data["portfolio_paper"]["state_dir"] = str(tmp_path / "portfolio_paper")
    data["portfolio_paper"]["decision_log_dir"] = str(tmp_path / "decisions")
    data["portfolio_paper"]["require_campaign_reference"] = require_campaign
    data["portfolio_paper"]["max_iterations"] = 1
    data["portfolio_paper"]["resume_existing_state"] = False
    data["portfolio_risk"]["max_new_positions_per_iteration"] = 2
    data["experiments"]["output_dir"] = str(tmp_path / "campaigns")
    data["reporting"]["output_dir"] = str(tmp_path / "reports")
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_run_portfolio_paper_help_works() -> None:
    result = CliRunner().invoke(app, ["run-portfolio-paper", "--help"])

    assert result.exit_code == 0


def test_report_portfolio_paper_help_works() -> None:
    result = CliRunner().invoke(app, ["report-portfolio-paper", "--help"])

    assert result.exit_code == 0


def test_portfolio_paper_refuses_missing_campaign_gate(tmp_path: Path) -> None:
    config = make_config(tmp_path, require_campaign=True)

    result = CliRunner().invoke(app, ["run-portfolio-paper", "--config", str(config)])

    assert result.exit_code == 1
    assert "campaign run id" in result.output


def test_portfolio_paper_runs_when_campaign_gate_disabled(tmp_path: Path) -> None:
    config = make_config(tmp_path, require_campaign=False)
    generate_fixtures(tmp_path / "raw")

    result = CliRunner().invoke(
        app,
        [
            "run-portfolio-paper",
            "--config",
            str(config),
            "--exchange",
            "kraken",
            "--symbols",
            "BTC/USDT,ETH/USDT",
            "--timeframe",
            "4h",
            "--max-iterations",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    run_dir = next((tmp_path / "portfolio_paper").iterdir())
    for filename in [
        "state.json",
        "orders.parquet",
        "trades.parquet",
        "equity_curve.parquet",
        "exposure_snapshots.parquet",
        "health_events.jsonl",
        "alerts.jsonl",
        "run_metadata.json",
    ]:
        assert (run_dir / filename).exists()
    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["live_trading"] is False


def test_portfolio_paper_runs_with_campaign_reference(tmp_path: Path) -> None:
    config = make_config(tmp_path, require_campaign=True)
    generate_fixtures(tmp_path / "raw")
    campaign_dir = tmp_path / "campaigns" / "campaign_fixture"
    campaign_dir.mkdir(parents=True)

    result = CliRunner().invoke(
        app,
        [
            "run-portfolio-paper",
            "--config",
            str(config),
            "--exchange",
            "kraken",
            "--symbols",
            "BTC/USDT,ETH/USDT",
            "--timeframe",
            "4h",
            "--campaign-run-id",
            "campaign_fixture",
            "--max-iterations",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output

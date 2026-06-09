from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from scripts.generate_fixture_data import generate_fixtures
from trading_bot.main import app
from trading_bot.reporting.portfolio_paper_report import LIMITATIONS

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


def test_portfolio_report_writes_all_required_artifacts(tmp_path: Path) -> None:
    config = make_config(tmp_path, require_campaign=False)
    generate_fixtures(tmp_path / "raw")
    runner = CliRunner()
    run = runner.invoke(
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
    assert run.exit_code == 0, run.output
    run_id = next((tmp_path / "portfolio_paper").iterdir()).name

    report = runner.invoke(
        app,
        [
            "report-portfolio-paper",
            "--config",
            str(config),
            "--portfolio-paper-run-id",
            run_id,
        ],
    )

    assert report.exit_code == 0, report.output
    report_dir = next((tmp_path / "reports").iterdir())
    for filename in [
        "config_snapshot.yaml",
        "portfolio_summary.json",
        "portfolio_metrics.json",
        "exposure_summary.json",
        "health_summary.json",
        "alert_summary.json",
        "readiness_gates.json",
        "report.md",
        "report.html",
        "run_metadata.json",
    ]:
        assert (report_dir / filename).exists()
    assert LIMITATIONS in (report_dir / "report.md").read_text(encoding="utf-8")


def test_portfolio_report_help_fixture_config_is_valid(tmp_path: Path) -> None:
    config = make_config(tmp_path, require_campaign=False)
    data = yaml.safe_load(config.read_text(encoding="utf-8"))

    assert data["portfolio_paper"]["require_campaign_reference"] is False

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
from typer.testing import CliRunner

from trading_bot.main import app
from trading_bot.paper.state import new_paper_state
from trading_bot.paper.store import PaperStateStore

REPO_ROOT = Path(__file__).resolve().parents[1]


def make_config(tmp_path: Path) -> Path:
    data = yaml.safe_load((REPO_ROOT / "config/default.yaml").read_text(encoding="utf-8"))
    data["paper"]["state_dir"] = str(tmp_path / "paper")
    data["reporting"]["output_dir"] = str(tmp_path / "reports")
    data["readiness"]["min_paper_runtime_days"] = 0
    data["readiness"]["min_paper_trades"] = 0
    data["readiness"]["require_validation_reference"] = False
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def make_run(tmp_path: Path) -> None:
    store = PaperStateStore(tmp_path / "paper")
    state = new_paper_state(
        exchange="kraken",
        symbol="BTC/USDT",
        timeframe="4h",
        strategy="noop",
        starting_equity=1000,
        paper_run_id="paper-1",
    )
    state.created_at = datetime.now(UTC) - timedelta(days=2)
    state.updated_at = datetime.now(UTC)
    state.equity = 1000
    state.equity_curve = [
        {"timestamp": state.created_at, "equity": 1000, "position_quantity": 0},
        {"timestamp": state.updated_at, "equity": 1000, "position_quantity": 0},
    ]
    store.save(
        state,
        {
            "paper_run_id": "paper-1",
            "live_trading": False,
            "real_orders_enabled": False,
            "uses_private_api": False,
        },
    )


def test_report_paper_help_works() -> None:
    result = CliRunner().invoke(app, ["report-paper", "--help"])

    assert result.exit_code == 0


def test_report_fails_cleanly_when_paper_run_is_missing(tmp_path: Path) -> None:
    config = make_config(tmp_path)

    result = CliRunner().invoke(
        app, ["report-paper", "--config", str(config), "--paper-run-id", "missing"]
    )

    assert result.exit_code == 1
    assert "missing paper run" in result.output


def test_report_writes_all_required_artifacts_for_valid_fixture_paper_run(tmp_path: Path) -> None:
    make_run(tmp_path)
    config = make_config(tmp_path)

    result = CliRunner().invoke(
        app, ["report-paper", "--config", str(config), "--paper-run-id", "paper-1"]
    )

    assert result.exit_code == 0, result.output
    run_dirs = list((tmp_path / "reports").iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    for filename in [
        "config_snapshot.yaml",
        "paper_summary.json",
        "paper_metrics.json",
        "readiness_gates.json",
        "health_summary.json",
        "alert_summary.json",
        "comparison_summary.json",
        "report.md",
        "report.html",
        "run_metadata.json",
    ]:
        assert (run_dir / filename).exists()
    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["live_trading"] is False

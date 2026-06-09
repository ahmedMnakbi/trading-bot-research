from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
from typer.testing import CliRunner

from trading_bot.data.cache import OhlcvCache
from trading_bot.data.models import OhlcvCandle
from trading_bot.main import app

REPO_ROOT = Path(__file__).resolve().parents[1]


def make_config(tmp_path: Path) -> Path:
    data = yaml.safe_load((REPO_ROOT / "config/default.yaml").read_text(encoding="utf-8"))
    data["data"]["cache_dir"] = str(tmp_path / "cache")
    data["experiments"]["output_dir"] = str(tmp_path / "campaigns")
    data["experiments"]["symbols"] = ["BTC/USDT"]
    data["experiments"]["timeframes"] = ["4h"]
    data["experiments"]["strategies"] = ["donchian_breakout"]
    data["experiments"]["review_gates"]["min_validation_windows"] = 1
    data["experiments"]["review_gates"]["min_total_test_trades"] = 0
    data["experiments"]["review_gates"]["require_no_high_severity_warnings"] = False
    data["validation"]["walk_forward"]["train_bars"] = 10
    data["validation"]["walk_forward"]["test_bars"] = 5
    data["validation"]["walk_forward"]["step_bars"] = 5
    data["strategy"]["params"]["donchian_lookback"] = 3
    data["strategy"]["params"]["atr_period"] = 3
    data["risk"]["max_stop_distance_pct"] = 50
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def write_cache(tmp_path: Path) -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    candles = [
        OhlcvCandle(
            timestamp=start + timedelta(hours=4 * index),
            open=100 + index,
            high=103 + index,
            low=97 + index,
            close=101 + index,
            volume=1,
        )
        for index in range(30)
    ]
    OhlcvCache(tmp_path / "cache").merge_and_write("kraken", "BTC/USDT", "4h", candles)


def test_run_campaign_help_works() -> None:
    assert CliRunner().invoke(app, ["run-campaign", "--help"]).exit_code == 0


def test_campaign_writes_all_required_artifacts(tmp_path: Path) -> None:
    write_cache(tmp_path)
    config = make_config(tmp_path)
    result = CliRunner().invoke(
        app, ["run-campaign", "--config", str(config), "--exchange", "kraken"]
    )
    assert result.exit_code == 0, result.output
    run_dir = next((tmp_path / "campaigns").iterdir())
    for filename in [
        "config_snapshot.yaml",
        "campaign_summary.json",
        "experiment_matrix.json",
        "experiment_results.json",
        "benchmark_summary.json",
        "warning_summary.json",
        "candidate_labels.json",
        "failed_runs.json",
        "report.md",
        "report.html",
        "run_metadata.json",
        "artifact_manifest.json",
    ]:
        assert (run_dir / filename).exists()
    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["live_trading"] is False
    assert metadata["real_orders_enabled"] is False
    assert metadata["uses_private_api"] is False
    assert metadata["optimization_used"] is False
    assert metadata["paper_trading_used"] is False


def test_completed_experiment_appears_in_results(tmp_path: Path) -> None:
    write_cache(tmp_path)
    config = make_config(tmp_path)
    CliRunner().invoke(app, ["run-campaign", "--config", str(config), "--exchange", "kraken"])
    run_dir = next((tmp_path / "campaigns").iterdir())
    results = json.loads((run_dir / "experiment_results.json").read_text(encoding="utf-8"))
    assert results

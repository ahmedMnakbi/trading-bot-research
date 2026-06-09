from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from trading_bot.main import app

REPO_ROOT = Path(__file__).resolve().parents[1]


def make_config(tmp_path: Path, *, require_validation: bool) -> Path:
    data = yaml.safe_load((REPO_ROOT / "config/default.yaml").read_text(encoding="utf-8"))
    data["paper"]["require_validation_run"] = require_validation
    data["paper"]["allow_public_live_data"] = False
    data["paper"]["state_dir"] = str(tmp_path / "paper")
    data["paper"]["decision_log_dir"] = str(tmp_path / "decisions")
    data["paper"]["max_iterations"] = 1
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_run_paper_help_works() -> None:
    result = CliRunner().invoke(app, ["run-paper", "--help"])

    assert result.exit_code == 0


def test_paper_trading_refuses_missing_validation_gate(tmp_path) -> None:  # type: ignore[no-untyped-def]
    config = make_config(tmp_path, require_validation=True)

    result = CliRunner().invoke(app, ["run-paper", "--config", str(config)])

    assert result.exit_code == 1
    assert "validation run" in result.output


def test_paper_trading_runs_when_validation_gate_disabled(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from datetime import UTC, datetime, timedelta

    from trading_bot.data.models import OhlcvCandle

    class FakeProvider:
        def fetch_ohlcv(self, symbol, timeframe, since_ms, limit):  # type: ignore[no-untyped-def]
            start = datetime(2024, 1, 1, tzinfo=UTC)
            return [
                OhlcvCandle(
                    timestamp=start + timedelta(hours=4 * index),
                    open=100 + index,
                    high=110 + index,
                    low=90 + index,
                    close=105 + index,
                    volume=1,
                )
                for index in range(3)
            ]

    monkeypatch.setattr("trading_bot.main.CcxtOhlcvProvider", lambda *a, **k: FakeProvider())
    config = make_config(tmp_path, require_validation=False)
    raw = yaml.safe_load(config.read_text(encoding="utf-8"))
    raw["paper"]["allow_public_live_data"] = True
    config.write_text(yaml.safe_dump(raw), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "run-paper",
            "--config",
            str(config),
            "--exchange",
            "kraken",
            "--symbol",
            "BTC/USDT",
            "--timeframe",
            "4h",
            "--strategy",
            "noop",
            "--max-iterations",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    run_dirs = list((tmp_path / "paper").iterdir())
    run_dir = run_dirs[0]
    for filename in [
        "state.json",
        "orders.parquet",
        "trades.parquet",
        "equity_curve.parquet",
        "health_events.jsonl",
        "alerts.jsonl",
        "run_metadata.json",
    ]:
        assert (run_dir / filename).exists()

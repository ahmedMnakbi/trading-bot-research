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


def make_validation_config(tmp_path: Path, *, cache_dir: Path) -> Path:
    data = yaml.safe_load((REPO_ROOT / "config/default.yaml").read_text(encoding="utf-8"))
    data["data"]["cache_dir"] = str(cache_dir)
    data["validation"]["min_train_bars"] = 10
    data["validation"]["min_test_bars"] = 5
    data["validation"]["walk_forward"]["train_bars"] = 20
    data["validation"]["walk_forward"]["test_bars"] = 10
    data["validation"]["walk_forward"]["step_bars"] = 10
    data["validation"]["regime"]["trend_ma_period"] = 10
    data["validation"]["regime"]["volatility_window"] = 5
    data["strategy"]["params"]["donchian_lookback"] = 5
    data["strategy"]["params"]["ema_fast"] = 3
    data["strategy"]["params"]["ema_slow"] = 8
    data["strategy"]["params"]["atr_period"] = 3
    data["risk"]["max_stop_distance_pct"] = 50
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def write_validation_cache(cache_dir: Path, rows: int = 80) -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    candles = []
    for index in range(rows):
        close = 100 + index * 0.5 + (index % 7)
        candles.append(
            OhlcvCandle(
                timestamp=start + timedelta(hours=4 * index),
                open=close,
                high=close + 2,
                low=close - 2,
                close=close,
                volume=1,
            )
        )
    OhlcvCache(cache_dir).merge_and_write("kraken", "BTC/USDT", "4h", candles)


def test_validation_cli_writes_all_required_artifacts(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    cache_dir = tmp_path / "cache"
    write_validation_cache(cache_dir)
    config = make_validation_config(tmp_path, cache_dir=cache_dir)

    result = CliRunner().invoke(
        app,
        [
            "run-validation",
            "--config",
            str(config),
            "--exchange",
            "kraken",
            "--symbol",
            "BTC/USDT",
            "--timeframe",
            "4h",
        ],
    )

    assert result.exit_code == 0, result.output
    run_dirs = list((tmp_path / "data" / "processed" / "validations").iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    for filename in [
        "config_snapshot.yaml",
        "validation_summary.json",
        "static_split_results.json",
        "walk_forward_results.json",
        "benchmark_comparison.json",
        "regime_performance.json",
        "warnings.json",
        "run_metadata.json",
    ]:
        assert (run_dir / filename).exists()
    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["live_trading"] is False
    assert metadata["optimization_used"] is False


def test_validation_fails_cleanly_when_cache_is_missing(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    config = make_validation_config(tmp_path, cache_dir=tmp_path / "missing")

    result = CliRunner().invoke(
        app,
        [
            "run-validation",
            "--config",
            str(config),
            "--exchange",
            "kraken",
            "--symbol",
            "BTC/USDT",
            "--timeframe",
            "4h",
        ],
    )

    assert result.exit_code == 1
    assert "missing cache file" in result.output


def test_validation_handles_zero_trade_strategy_without_crashing(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    cache_dir = tmp_path / "cache"
    write_validation_cache(cache_dir)
    config = make_validation_config(tmp_path, cache_dir=cache_dir)
    raw = yaml.safe_load(config.read_text(encoding="utf-8"))
    raw["validation"]["strategies"] = ["noop"]
    config.write_text(yaml.safe_dump(raw), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "run-validation",
            "--config",
            str(config),
            "--exchange",
            "kraken",
            "--symbol",
            "BTC/USDT",
            "--timeframe",
            "4h",
        ],
    )

    assert result.exit_code == 0, result.output

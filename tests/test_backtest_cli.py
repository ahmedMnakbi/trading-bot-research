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


def make_config(tmp_path: Path, *, cache_dir: Path) -> Path:
    data = yaml.safe_load((REPO_ROOT / "config/default.yaml").read_text(encoding="utf-8"))
    data["data"]["cache_dir"] = str(cache_dir)
    data["backtesting"]["max_bars"] = None
    data["risk"]["max_stop_distance_pct"] = 50
    data["strategy"]["params"]["donchian_lookback"] = 5
    data["strategy"]["params"]["ema_fast"] = 3
    data["strategy"]["params"]["ema_slow"] = 8
    data["strategy"]["params"]["atr_period"] = 3
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def write_cache(cache_dir: Path) -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    candles = [
        OhlcvCandle(
            timestamp=start + timedelta(hours=4 * index),
            open=100 + index,
            high=110 + index,
            low=90 + index,
            close=105 + index,
            volume=1,
        )
        for index in range(4)
    ]
    OhlcvCache(cache_dir).merge_and_write("kraken", "BTC/USDT", "4h", candles)


def write_strategy_cache(cache_dir: Path) -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    closes = [100] * 10 + [99, 101, 104, 107, 110, 113, 116, 119, 122]
    candles = [
        OhlcvCandle(
            timestamp=start + timedelta(hours=4 * index),
            open=close,
            high=close + 2,
            low=close - 2,
            close=close,
            volume=1,
        )
        for index, close in enumerate(closes)
    ]
    OhlcvCache(cache_dir).merge_and_write("kraken", "BTC/USDT", "4h", candles)


def test_cli_fails_cleanly_when_cache_is_missing(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    config = make_config(tmp_path, cache_dir=tmp_path / "missing-cache")

    result = CliRunner().invoke(
        app,
        [
            "run-backtest",
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
        ],
    )

    assert result.exit_code == 1
    assert "missing cache file" in result.output


def test_cli_writes_all_required_result_artifacts(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    cache_dir = tmp_path / "cache"
    write_cache(cache_dir)
    config = make_config(tmp_path, cache_dir=cache_dir)

    result = CliRunner().invoke(
        app,
        [
            "run-backtest",
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
        ],
    )

    assert result.exit_code == 0, result.output
    run_dirs = list((tmp_path / "data" / "processed" / "backtests").iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    for filename in [
        "config_snapshot.yaml",
        "metrics.json",
        "equity_curve.parquet",
        "trades.parquet",
        "orders.parquet",
        "run_metadata.json",
    ]:
        assert (run_dir / filename).exists()
    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["live_trading"] is False


def test_cli_runs_fixture_backtest_with_donchian_breakout(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    cache_dir = tmp_path / "cache"
    write_strategy_cache(cache_dir)
    config = make_config(tmp_path, cache_dir=cache_dir)

    result = CliRunner().invoke(
        app,
        [
            "run-backtest",
            "--config",
            str(config),
            "--exchange",
            "kraken",
            "--symbol",
            "BTC/USDT",
            "--timeframe",
            "4h",
            "--strategy",
            "donchian_breakout",
        ],
    )

    assert result.exit_code == 0, result.output


def test_cli_runs_fixture_backtest_with_ema_trend(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    cache_dir = tmp_path / "cache"
    write_strategy_cache(cache_dir)
    config = make_config(tmp_path, cache_dir=cache_dir)

    result = CliRunner().invoke(
        app,
        [
            "run-backtest",
            "--config",
            str(config),
            "--exchange",
            "kraken",
            "--symbol",
            "BTC/USDT",
            "--timeframe",
            "4h",
            "--strategy",
            "ema_trend",
        ],
    )

    assert result.exit_code == 0, result.output

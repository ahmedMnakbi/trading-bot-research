from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from trading_bot.config.settings import Settings
from trading_bot.data.cache import OhlcvCache
from trading_bot.data.models import OhlcvCandle
from trading_bot.experiments.campaign import build_experiment_matrix
from trading_bot.experiments.runner import run_campaign


def make_settings(tmp_path: Path) -> Settings:
    data = yaml.safe_load(Path("config/default.yaml").read_text(encoding="utf-8"))
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
    return Settings.model_validate(data)


def write_cache(settings: Settings, rows: int = 30) -> None:
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
        for index in range(rows)
    ]
    OhlcvCache(settings.data.cache_dir).merge_and_write("kraken", "BTC/USDT", "4h", candles)


def test_campaign_runner_builds_expected_experiment_matrix() -> None:
    matrix = build_experiment_matrix(
        exchange="kraken",
        symbols=["BTC/USDT", "ETH/USDT"],
        timeframes=["4h"],
        strategies=["noop", "buy_and_hold"],
        stages=["backtest", "validation"],
    )
    assert len(matrix) == 4


def test_campaign_uses_cached_data_only_by_default(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    assert settings.experiments.use_cached_data_only is True


def test_campaign_fails_cleanly_when_cached_data_missing(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    output = run_campaign(settings=settings, config_snapshot={}, exchange="kraken")
    assert (output / "failed_runs.json").exists()


def test_one_failed_experiment_does_not_crash_full_campaign(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_cache(settings)
    output = run_campaign(
        settings=settings,
        config_snapshot={},
        exchange="kraken",
        symbols=["BTC/USDT", "MISSING/USDT"],
    )
    assert (output / "failed_runs.json").exists()
    assert (output / "experiment_results.json").exists()


import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from trading_bot.mt5.cache import Mt5RatesCache
from trading_bot.mt5.data import rates_to_bars
from trading_bot.mt5.validation import run_mt5_campaign_from_cache, run_mt5_validation_from_cache


def _write_cache(tmp_path: Path, symbol: str = "EURUSD") -> Path:
    cache_dir = tmp_path / "mt5_rates"
    start = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)
    raw = []
    price = 100.0
    for index in range(120):
        timestamp = start + timedelta(minutes=5 * index)
        price += 0.2
        raw.append(
            {
                "time": int(timestamp.timestamp()),
                "open": price - 0.1,
                "high": price + 0.6,
                "low": price - 0.6,
                "close": price,
                "tick_volume": float(100 + index),
                "spread": 10,
            }
        )
    Mt5RatesCache(cache_dir).merge_and_write("demo_broker", symbol, "5m", rates_to_bars(raw))
    return cache_dir


def test_mt5_validation_writes_static_and_walk_forward_artifacts(tmp_path: Path) -> None:
    output_dir = run_mt5_validation_from_cache(
        cache_dir=_write_cache(tmp_path),
        output_root=tmp_path / "validations",
        broker="demo_broker",
        symbol="EURUSD",
        timeframe="5m",
        strategies=["vwap_trend_continuation"],
        min_train_bars=40,
        min_test_bars=20,
        walk_forward_train_bars=40,
        walk_forward_test_bars=20,
        walk_forward_step_bars=20,
        run_id="mt5_validation_fixture",
    )

    assert (output_dir / "validation_summary.json").exists()
    assert (output_dir / "static_split_results.json").exists()
    assert (output_dir / "walk_forward_results.json").exists()
    metadata = json.loads((output_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["live_trading"] is False
    assert metadata["real_orders_enabled"] is False
    assert metadata["uses_private_api"] is False


def test_mt5_campaign_labels_completed_experiment(tmp_path: Path) -> None:
    output_dir = run_mt5_campaign_from_cache(
        cache_dir=_write_cache(tmp_path),
        output_root=tmp_path / "campaigns",
        broker="demo_broker",
        symbols=["EURUSD"],
        timeframes=["5m"],
        strategies=["vwap_trend_continuation"],
        min_validation_windows=1,
        min_total_test_trades=1,
        run_id="mt5_campaign_fixture",
    )

    summary = json.loads((output_dir / "campaign_summary.json").read_text(encoding="utf-8"))
    labels = json.loads((output_dir / "candidate_labels.json").read_text(encoding="utf-8"))
    metadata = json.loads((output_dir / "run_metadata.json").read_text(encoding="utf-8"))

    assert summary["completed"] == 1
    assert summary["failed"] == 0
    assert list(labels.values())[0]["label"] in {
        "PAPER_OBSERVATION_ONLY",
        "NEEDS_MORE_DATA",
        "REJECTED",
    }
    assert metadata["real_orders_enabled"] is False

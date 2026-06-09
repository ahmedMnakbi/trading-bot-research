from datetime import UTC, datetime, timedelta
from pathlib import Path

from trading_bot.mt5.backtesting import (
    Mt5BacktestMarketModel,
    run_mt5_backtest_from_cache,
)
from trading_bot.mt5.cache import Mt5RatesCache
from trading_bot.mt5.data import rates_to_bars


def _write_trending_cache(tmp_path: Path, *, down: bool = False) -> Path:
    cache_dir = tmp_path / "mt5_rates"
    start = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)
    raw = []
    price = 100.0
    for index in range(80):
        timestamp = start + timedelta(minutes=5 * index)
        price = price - 0.25 if down else price + 0.25
        raw.append(
            {
                "time": int(timestamp.timestamp()),
                "open": price - 0.1 if not down else price + 0.1,
                "high": price + 0.6,
                "low": price - 0.6,
                "close": price,
                "tick_volume": 100 + index,
                "spread": 10,
                "real_volume": 0,
            }
        )
    bars = rates_to_bars(raw)
    Mt5RatesCache(cache_dir).merge_and_write("demo_broker", "EURUSD", "5m", bars)
    return cache_dir


def test_mt5_backtest_runs_from_cache_and_writes_artifacts(tmp_path: Path) -> None:
    result = run_mt5_backtest_from_cache(
        cache_dir=_write_trending_cache(tmp_path),
        output_root=tmp_path / "runs",
        broker="demo_broker",
        symbol="EURUSD",
        timeframe="5m",
        strategy_name="vwap_trend_continuation",
        market_model=Mt5BacktestMarketModel(
            fee_bps=1,
            slippage_points=0.01,
            min_stop_distance_points=0.01,
        ),
        config_snapshot={"test": True},
        run_id="mt5_fixture_backtest",
    )

    assert result.run_id == "mt5_fixture_backtest"
    assert result.output_dir.exists()
    assert (result.output_dir / "metrics.json").exists()
    assert (result.output_dir / "orders.parquet").exists()
    assert result.metadata["live_trading"] is False
    assert result.metadata["real_orders_enabled"] is False
    assert result.metrics["number_of_trades"] >= 1


def test_mt5_backtest_rejects_short_signals_when_shorting_disabled(tmp_path: Path) -> None:
    result = run_mt5_backtest_from_cache(
        cache_dir=_write_trending_cache(tmp_path, down=True),
        output_root=tmp_path / "runs",
        broker="demo_broker",
        symbol="EURUSD",
        timeframe="5m",
        strategy_name="vwap_trend_continuation",
        market_model=Mt5BacktestMarketModel(allow_shorting=False),
        config_snapshot={"test": True},
        run_id="mt5_short_rejected",
    )

    assert result.metrics["number_of_trades"] == 0
    assert "shorting_disabled_for_research_run" in set(result.orders["reason"])


def test_mt5_backtest_rejects_invalid_stop_distance(tmp_path: Path) -> None:
    result = run_mt5_backtest_from_cache(
        cache_dir=_write_trending_cache(tmp_path),
        output_root=tmp_path / "runs",
        broker="demo_broker",
        symbol="EURUSD",
        timeframe="5m",
        strategy_name="vwap_trend_continuation",
        market_model=Mt5BacktestMarketModel(min_stop_distance_points=100),
        config_snapshot={"test": True},
        run_id="mt5_stop_rejected",
    )

    assert result.metrics["number_of_trades"] == 0
    assert "invalid_stop_distance" in set(result.orders["reason"])

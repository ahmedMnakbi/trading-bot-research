from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from trading_bot.backtesting.engine import run_backtest_from_cache
from trading_bot.data.cache import OhlcvCache
from trading_bot.data.models import OhlcvCandle
from trading_bot.strategies.buy_and_hold import BuyAndHoldStrategy
from trading_bot.strategies.noop import NoopStrategy


def candle_at(timestamp: datetime, open_: float, close: float | None = None) -> OhlcvCandle:
    close_price = close if close is not None else open_
    return OhlcvCandle(
        timestamp=timestamp,
        open=open_,
        high=max(open_, close_price) + 5,
        low=min(open_, close_price) - 5,
        close=close_price,
        volume=1,
    )


def write_fixture_cache(tmp_path: Path) -> Path:
    cache_dir = tmp_path / "cache"
    start = datetime(2024, 1, 1, tzinfo=UTC)
    candles = [
        candle_at(start + timedelta(hours=4 * index), open_=100 + index * 10)
        for index in range(5)
    ]
    OhlcvCache(cache_dir).merge_and_write("kraken", "BTC/USDT", "4h", candles)
    return cache_dir


def run_fixture_backtest(tmp_path: Path, strategy) -> object:  # type: ignore[no-untyped-def]
    return run_backtest_from_cache(
        cache_dir=write_fixture_cache(tmp_path),
        output_root=tmp_path / "runs",
        exchange="kraken",
        symbol="BTC/USDT",
        timeframe="4h",
        strategy=strategy,
        starting_equity=10000,
        fee_bps=10,
        slippage_bps=5,
        allow_shorting=False,
        allow_leverage=False,
        reject_orders_without_stop=True,
        min_cash_pct=5,
        mark_to_market=True,
        config_snapshot={"test": True},
        run_id=f"run_{strategy.name}",
    )


def test_noop_strategy_produces_no_trades(tmp_path: Path) -> None:
    result = run_fixture_backtest(tmp_path, NoopStrategy())

    assert result.metrics["number_of_trades"] == 0
    assert result.trades.empty


def test_buy_and_hold_produces_exactly_one_entry_and_one_exit(tmp_path: Path) -> None:
    result = run_fixture_backtest(tmp_path, BuyAndHoldStrategy())

    assert result.metrics["number_of_trades"] == 1
    assert len(result.orders[result.orders["status"] == "FILLED"]) == 2


def test_backtest_engine_uses_next_candle_open_for_fills(tmp_path: Path) -> None:
    result = run_fixture_backtest(tmp_path, BuyAndHoldStrategy())
    first_order = result.orders.iloc[0]

    assert first_order["requested_price"] == 110


def test_backtest_results_include_fees_and_slippage(tmp_path: Path) -> None:
    result = run_fixture_backtest(tmp_path, BuyAndHoldStrategy())

    assert result.metrics["fees_paid"] > 0
    assert result.metrics["slippage_paid_estimate"] > 0


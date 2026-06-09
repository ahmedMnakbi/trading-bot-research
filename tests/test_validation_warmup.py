from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
from typer.testing import CliRunner

from trading_bot.backtesting.engine import run_backtest_on_candles
from trading_bot.backtesting.events import TradeIntent
from trading_bot.data.cache import OhlcvCache
from trading_bot.data.models import OhlcvCandle
from trading_bot.main import app
from trading_bot.portfolio.account import AccountState

REPO_ROOT = Path(__file__).resolve().parents[1]


class RecordingEntryStrategy:
    name = "recording_entry"

    def __init__(self) -> None:
        self.visible_lengths: list[int] = []

    def generate_signal(self, candles, current_index: int, account: AccountState) -> TradeIntent:  # type: ignore[no-untyped-def]
        self.visible_lengths.append(len(candles))
        if current_index == 0 and account.position is None:
            return TradeIntent(
                action="BUY",
                reason="strategy_entry",
                stop_loss=float(candles["close"].iloc[-1]) * 0.95,
            )
        return TradeIntent.hold("hold")


def _candles(closes: list[float]) -> list[OhlcvCandle]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    return [
        OhlcvCandle(
            timestamp=start + timedelta(hours=4 * index),
            open=close,
            high=close + 3,
            low=close - 3,
            close=close,
            volume=1,
        )
        for index, close in enumerate(closes)
    ]


def test_warmup_context_starts_trading_at_test_boundary_without_lookahead() -> None:
    candles = _candles([100, 101, 102, 103, 104, 105, 106])
    strategy = RecordingEntryStrategy()

    result = run_backtest_on_candles(
        candles=candles,
        output_root=Path("unused"),
        exchange="sandbox",
        symbol="BTC/USDT",
        timeframe="4h",
        strategy=strategy,
        starting_equity=10_000,
        fee_bps=10,
        slippage_bps=5,
        allow_shorting=False,
        allow_leverage=False,
        reject_orders_without_stop=True,
        min_cash_pct=5,
        mark_to_market=True,
        config_snapshot={},
        risk_per_trade_pct=0.25,
        max_total_exposure_pct=30,
        min_stop_distance_bps=10,
        max_stop_distance_pct=50,
        trade_start_index=4,
        write_artifacts=False,
    )

    assert strategy.visible_lengths[0] == 4
    assert result.orders.iloc[0]["timestamp"] == candles[4].timestamp
    assert result.equity_curve.iloc[0]["timestamp"] == candles[4].timestamp
    assert result.orders["timestamp"].min() >= candles[4].timestamp


def test_validation_ema_can_trade_with_historical_warmup_context(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    cache_dir = tmp_path / "cache"
    OhlcvCache(cache_dir).merge_and_write(
        "binance",
        "BTC/USDT",
        "4h",
        _candles([100] * 8 + [99, 110] + [112, 114, 116, 118, 120]),
    )
    data = yaml.safe_load((REPO_ROOT / "config/default.yaml").read_text(encoding="utf-8"))
    data["data"]["cache_dir"] = str(cache_dir)
    data["validation"]["strategies"] = ["ema_trend"]
    data["validation"]["benchmarks"] = ["buy_and_hold"]
    data["validation"]["min_train_bars"] = 8
    data["validation"]["min_test_bars"] = 5
    data["validation"]["train_pct"] = 67
    data["validation"]["test_pct"] = 33
    data["validation"]["walk_forward"]["train_bars"] = 10
    data["validation"]["walk_forward"]["test_bars"] = 5
    data["validation"]["walk_forward"]["step_bars"] = 5
    data["validation"]["regime"]["trend_ma_period"] = 3
    data["validation"]["regime"]["volatility_window"] = 3
    data["strategy"]["params"]["ema_fast"] = 3
    data["strategy"]["params"]["ema_slow"] = 8
    data["strategy"]["params"]["atr_period"] = 3
    data["risk"]["max_stop_distance_pct"] = 50
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump(data), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "run-validation",
            "--config",
            str(config),
            "--exchange",
            "binance",
            "--symbol",
            "BTC/USDT",
            "--timeframe",
            "4h",
        ],
    )

    assert result.exit_code == 0, result.output
    run_dir = next((tmp_path / "data" / "processed" / "validations").iterdir())
    walk_forward = json.loads((run_dir / "walk_forward_results.json").read_text(encoding="utf-8"))
    assert walk_forward["ema_trend"]["aggregate"]["total_test_trades"] > 0

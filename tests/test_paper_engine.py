from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trading_bot.data.models import OhlcvCandle
from trading_bot.execution.simulated import SimulatedExecutionClient
from trading_bot.paper.decision_log import PaperDecisionLogger
from trading_bot.paper.engine import PaperTradingEngine
from trading_bot.paper.store import PaperStateStore
from trading_bot.strategies.buy_and_hold import BuyAndHoldStrategy
from trading_bot.strategies.noop import NoopStrategy


class FakeProvider:
    def __init__(self, candles):  # type: ignore[no-untyped-def]
        self.candles = candles

    def fetch_ohlcv(self, symbol: str, timeframe: str, since_ms: int, limit: int):  # type: ignore[no-untyped-def]
        return self.candles


class ErrorProvider:
    def fetch_ohlcv(self, symbol: str, timeframe: str, since_ms: int, limit: int):  # type: ignore[no-untyped-def]
        raise RuntimeError("data down")


def candles(count: int = 3) -> list[OhlcvCandle]:
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
        for index in range(count)
    ]


def make_engine(tmp_path, provider, strategy=None, max_errors=3):  # type: ignore[no-untyped-def]
    return PaperTradingEngine(
        provider=provider,
        execution=SimulatedExecutionClient(fee_bps=0, slippage_bps=0),
        store=PaperStateStore(tmp_path / "state"),
        decision_logger=PaperDecisionLogger(tmp_path / "decisions"),
        strategy=strategy or NoopStrategy(),
        exchange="kraken",
        symbol="BTC/USDT",
        timeframe="4h",
        starting_equity=1000,
        fee_bps=0,
        risk_per_trade_pct=1,
        max_total_exposure_pct=100,
        min_stop_distance_bps=1,
        max_stop_distance_pct=50,
        max_consecutive_data_errors=max_errors,
        allow_partial_latest_candle=True,
        resume_existing_state=True,
        persist_state=True,
        validation_run_id=None,
    )


def test_paper_engine_creates_state_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = make_engine(tmp_path, FakeProvider(candles())).run(max_iterations=1)

    assert (tmp_path / "state" / state.paper_run_id / "state.json").exists()


def test_paper_engine_resumes_existing_state_when_configured(tmp_path) -> None:  # type: ignore[no-untyped-def]
    first = make_engine(tmp_path, FakeProvider(candles())).run(max_iterations=1)
    second = make_engine(tmp_path, FakeProvider(candles())).run(max_iterations=1)

    assert second.paper_run_id == first.paper_run_id


def test_paper_engine_does_not_reprocess_same_candle_twice(tmp_path) -> None:  # type: ignore[no-untyped-def]
    engine = make_engine(tmp_path, FakeProvider(candles()))
    first = engine.run(max_iterations=1)
    second = make_engine(tmp_path, FakeProvider(candles())).run(max_iterations=1)

    assert second.last_processed_candle_timestamp == first.last_processed_candle_timestamp


def test_paper_engine_handles_empty_public_data_response(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = make_engine(tmp_path, FakeProvider([])).run(max_iterations=1)

    assert state.consecutive_data_errors == 1


def test_paper_engine_activates_kill_switch_after_too_many_data_errors(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = make_engine(tmp_path, ErrorProvider(), max_errors=2).run(max_iterations=2)

    assert state.kill_switch_active is True


def test_paper_engine_writes_health_events_and_alerts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = make_engine(tmp_path, FakeProvider([])).run(max_iterations=1)
    run_dir = tmp_path / "state" / state.paper_run_id

    assert (run_dir / "health_events.jsonl").exists()
    assert (run_dir / "alerts.jsonl").exists()


def test_paper_engine_records_simulated_orders(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = make_engine(tmp_path, FakeProvider(candles()), strategy=BuyAndHoldStrategy()).run(
        max_iterations=1
    )

    assert state.orders

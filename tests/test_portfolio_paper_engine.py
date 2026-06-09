from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from trading_bot.backtesting.events import TradeIntent
from trading_bot.config.settings import PortfolioRiskSettings
from trading_bot.data.models import OhlcvCandle
from trading_bot.execution.simulated import SimulatedExecutionClient
from trading_bot.paper.portfolio_engine import PortfolioPaperTradingEngine
from trading_bot.paper.store import PortfolioPaperStateStore


class StaticProvider:
    def __init__(self, candles_by_symbol: dict[str, list[OhlcvCandle]]) -> None:
        self.candles_by_symbol = candles_by_symbol

    def fetch_ohlcv(
        self, symbol: str, timeframe: str, since_ms: int, limit: int
    ) -> list[OhlcvCandle]:
        return self.candles_by_symbol[symbol][-limit:]


class BuyOnceStrategy:
    name = "donchian_breakout"

    def generate_signal(self, candles, current_index, account):  # type: ignore[no-untyped-def]
        if account.position is not None:
            return TradeIntent.hold("already_open")
        return TradeIntent(
            action="BUY",
            reason="test_buy",
            stop_loss=float(candles.iloc[current_index]["close"]) * 0.95,
        )


def candles(symbol_offset: float = 0) -> list[OhlcvCandle]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    return [
        OhlcvCandle(
            timestamp=start + timedelta(hours=4 * index),
            open=100 + symbol_offset + index,
            high=110 + symbol_offset + index,
            low=90 + symbol_offset + index,
            close=105 + symbol_offset + index,
            volume=1,
        )
        for index in range(3)
    ]


def many_candles(symbol_offset: float = 0, rows: int = 500) -> list[OhlcvCandle]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    return [
        OhlcvCandle(
            timestamp=start + timedelta(hours=4 * index),
            open=100 + symbol_offset + index,
            high=110 + symbol_offset + index,
            low=90 + symbol_offset + index,
            close=105 + symbol_offset + index,
            volume=1,
        )
        for index in range(rows)
    ]


def risk(**overrides: object) -> PortfolioRiskSettings:
    data = {
        "max_open_positions": 3,
        "max_total_exposure_pct": 30,
        "max_symbol_exposure_pct": 15,
        "max_strategy_exposure_pct": 30,
        "max_new_positions_per_iteration": 2,
        "min_cash_pct": 5,
        "max_daily_loss_pct": 50,
        "max_weekly_loss_pct": 50,
        "max_drawdown_pct": 50,
        "reject_correlated_entries": False,
        "correlation_warning_threshold": 0.8,
    }
    data.update(overrides)
    return PortfolioRiskSettings.model_validate(data)


def make_engine(tmp_path: Path, *, resume: bool = True) -> PortfolioPaperTradingEngine:
    return PortfolioPaperTradingEngine(
        provider=StaticProvider({"BTC/USDT": candles(), "ETH/USDT": candles(50)}),
        execution=SimulatedExecutionClient(fee_bps=10, slippage_bps=5),
        store=PortfolioPaperStateStore(tmp_path),
        strategies={"BTC/USDT": BuyOnceStrategy(), "ETH/USDT": BuyOnceStrategy()},
        portfolio_risk=risk(),
        exchange="kraken",
        symbols=["BTC/USDT", "ETH/USDT"],
        timeframe="4h",
        starting_equity=10_000,
        fee_bps=10,
        risk_per_trade_pct=0.25,
        min_stop_distance_bps=10,
        max_stop_distance_pct=10,
        max_consecutive_data_errors=3,
        allow_partial_latest_candle=True,
        resume_existing_state=resume,
        persist_state=True,
        campaign_run_id=None,
    )


def make_engine_with(
    tmp_path: Path,
    *,
    candles_by_symbol: dict[str, list[OhlcvCandle]],
    portfolio_risk: PortfolioRiskSettings | None = None,
    resume: bool = False,
) -> PortfolioPaperTradingEngine:
    return PortfolioPaperTradingEngine(
        provider=StaticProvider(candles_by_symbol),
        execution=SimulatedExecutionClient(fee_bps=10, slippage_bps=5),
        store=PortfolioPaperStateStore(tmp_path),
        strategies={"BTC/USDT": BuyOnceStrategy(), "ETH/USDT": BuyOnceStrategy()},
        portfolio_risk=portfolio_risk or risk(),
        exchange="kraken",
        symbols=["BTC/USDT", "ETH/USDT"],
        timeframe="4h",
        starting_equity=10_000,
        fee_bps=10,
        risk_per_trade_pct=0.25,
        min_stop_distance_bps=10,
        max_stop_distance_pct=10,
        max_consecutive_data_errors=3,
        allow_partial_latest_candle=True,
        resume_existing_state=resume,
        persist_state=True,
        campaign_run_id=None,
    )


def test_portfolio_paper_engine_writes_required_artifacts(tmp_path: Path) -> None:
    state = make_engine(tmp_path, resume=False).run(max_iterations=1)
    run_dir = tmp_path / state.portfolio_paper_run_id

    for filename in [
        "state.json",
        "orders.parquet",
        "trades.parquet",
        "equity_curve.parquet",
        "exposure_snapshots.parquet",
        "health_events.jsonl",
        "alerts.jsonl",
        "run_metadata.json",
    ]:
        assert (run_dir / filename).exists()

    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["live_trading"] is False
    assert metadata["real_orders_enabled"] is False
    assert metadata["uses_private_api"] is False


def test_engine_avoids_reprocessing_same_candle_per_symbol(tmp_path: Path) -> None:
    first = make_engine(tmp_path, resume=True).run(max_iterations=1)
    run_dir = tmp_path / first.portfolio_paper_run_id
    decisions_before = (run_dir / "decisions.jsonl").read_text(encoding="utf-8")

    second = make_engine(tmp_path, resume=True).run(max_iterations=1)
    decisions_after = (run_dir / "decisions.jsonl").read_text(encoding="utf-8")

    assert second.portfolio_paper_run_id == first.portfolio_paper_run_id
    assert decisions_after == decisions_before


def test_max_iterations_processes_only_latest_candle_per_symbol(tmp_path: Path) -> None:
    state = make_engine_with(
        tmp_path,
        candles_by_symbol={
            "BTC/USDT": many_candles(),
            "ETH/USDT": many_candles(50),
        },
    ).run(max_iterations=3)
    run_dir = tmp_path / state.portfolio_paper_run_id

    decisions = (run_dir / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
    health = [
        json.loads(line)
        for line in (run_dir / "health_events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(decisions) == 2
    assert [event["code"] for event in health].count("DUPLICATE_CANDLE") == 4


def test_duplicate_candles_do_not_create_duplicate_decisions_orders_or_trades(
    tmp_path: Path,
) -> None:
    first = make_engine_with(
        tmp_path,
        candles_by_symbol={"BTC/USDT": candles(), "ETH/USDT": candles(50)},
        resume=True,
    ).run(max_iterations=1)
    run_dir = tmp_path / first.portfolio_paper_run_id
    decisions_before = (run_dir / "decisions.jsonl").read_text(encoding="utf-8")
    orders_before = len(first.orders)
    trades_before = len(first.trades)

    second = make_engine_with(
        tmp_path,
        candles_by_symbol={"BTC/USDT": candles(), "ETH/USDT": candles(50)},
        resume=True,
    ).run(max_iterations=1)

    assert (run_dir / "decisions.jsonl").read_text(encoding="utf-8") == decisions_before
    assert len(second.orders) == orders_before
    assert len(second.trades) == trades_before


def test_expected_portfolio_risk_rejections_are_health_only(tmp_path: Path) -> None:
    state = make_engine_with(
        tmp_path,
        candles_by_symbol={"BTC/USDT": candles(), "ETH/USDT": candles(50)},
        portfolio_risk=risk(max_new_positions_per_iteration=1),
    ).run(max_iterations=1)
    run_dir = tmp_path / state.portfolio_paper_run_id
    health = (run_dir / "health_events.jsonl").read_text(encoding="utf-8")
    alerts = (run_dir / "alerts.jsonl").read_text(encoding="utf-8")

    assert "PORTFOLIO_RISK_REJECTED" in health
    assert "PORTFOLIO_RISK_REJECTED" not in alerts


def test_portfolio_paper_smoke_has_explainable_health_output(tmp_path: Path) -> None:
    state = make_engine_with(
        tmp_path,
        candles_by_symbol={"BTC/USDT": candles(), "ETH/USDT": candles(50)},
    ).run(max_iterations=3)
    run_dir = tmp_path / state.portfolio_paper_run_id
    health_codes = {
        json.loads(line)["code"]
        for line in (run_dir / "health_events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    assert health_codes.issubset({"DUPLICATE_CANDLE", "PORTFOLIO_RISK_REJECTED"})
    assert state.kill_switch_active is False


def test_decision_log_includes_non_live_flags(tmp_path: Path) -> None:
    state = make_engine(tmp_path, resume=False).run(max_iterations=1)
    decision_line = (tmp_path / state.portfolio_paper_run_id / "decisions.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()[0]

    decision = json.loads(decision_line)
    assert decision["live_trading"] is False
    assert decision["real_order"] is False


def test_portfolio_execution_uses_simulated_client_only(tmp_path: Path) -> None:
    engine = make_engine(tmp_path, resume=False)

    assert isinstance(engine.execution, SimulatedExecutionClient)

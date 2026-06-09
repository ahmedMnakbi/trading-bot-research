from __future__ import annotations

from datetime import UTC, datetime

from trading_bot.portfolio.exposure import calculate_exposure_snapshot
from trading_bot.portfolio.portfolio_state import PortfolioPosition, new_portfolio_paper_state


def test_exposure_snapshot_calculates_gross_symbol_and_strategy_pct() -> None:
    state = new_portfolio_paper_state(
        exchange="kraken",
        timeframe="4h",
        symbols=["BTC/USDT", "ETH/USDT"],
        strategy_map={"BTC/USDT": "donchian_breakout", "ETH/USDT": "ema_trend"},
        starting_equity=10_000,
    )
    state.equity = 10_000
    state.positions_by_symbol["BTC/USDT"] = PortfolioPosition(
        symbol="BTC/USDT",
        strategy="donchian_breakout",
        quantity=0.02,
        entry_price=50_000,
    )
    state.positions_by_symbol["ETH/USDT"] = PortfolioPosition(
        symbol="ETH/USDT",
        strategy="ema_trend",
        quantity=0.5,
        entry_price=2_000,
    )

    snapshot = calculate_exposure_snapshot(
        state,
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        mark_prices={"BTC/USDT": 50_000, "ETH/USDT": 2_000},
    )

    assert snapshot["gross_exposure_pct"] == 20
    assert snapshot["symbol_exposure_pct"]["BTC/USDT"] == 10
    assert snapshot["strategy_exposure_pct"]["ema_trend"] == 10

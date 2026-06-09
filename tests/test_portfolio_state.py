from __future__ import annotations

from pathlib import Path

from trading_bot.paper.store import PortfolioPaperStateStore
from trading_bot.portfolio.portfolio_state import PortfolioPosition, new_portfolio_paper_state


def test_portfolio_state_creates_shared_cash_and_per_symbol_positions() -> None:
    state = new_portfolio_paper_state(
        exchange="kraken",
        timeframe="4h",
        symbols=["BTC/USDT", "ETH/USDT"],
        strategy_map={"BTC/USDT": "donchian_breakout", "ETH/USDT": "ema_trend"},
        starting_equity=10_000,
    )

    state.positions_by_symbol["BTC/USDT"] = PortfolioPosition(
        symbol="BTC/USDT",
        strategy="donchian_breakout",
        quantity=0.1,
        entry_price=50_000,
        stop_loss=49_000,
    )

    assert state.cash == 10_000
    assert "BTC/USDT" in state.positions_by_symbol
    assert state.last_processed_candle_by_symbol == {"BTC/USDT": None, "ETH/USDT": None}


def test_portfolio_state_resumes_existing_state(tmp_path: Path) -> None:
    store = PortfolioPaperStateStore(tmp_path)
    state = new_portfolio_paper_state(
        exchange="kraken",
        timeframe="4h",
        symbols=["BTC/USDT"],
        strategy_map={"BTC/USDT": "donchian_breakout"},
        starting_equity=10_000,
    )
    store.save(state, {"live_trading": False, "real_orders_enabled": False})

    resumed = store.latest_state(
        exchange="kraken",
        symbols=["BTC/USDT"],
        timeframe="4h",
        strategy_map={"BTC/USDT": "donchian_breakout"},
    )

    assert resumed is not None
    assert resumed.portfolio_paper_run_id == state.portfolio_paper_run_id

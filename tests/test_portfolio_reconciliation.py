from __future__ import annotations

from trading_bot.portfolio.portfolio_state import PortfolioPosition, new_portfolio_paper_state
from trading_bot.portfolio.reconciliation import reconcile_portfolio_state


def test_portfolio_reconciliation_reports_invalid_position() -> None:
    state = new_portfolio_paper_state(
        exchange="kraken",
        timeframe="4h",
        symbols=["BTC/USDT"],
        strategy_map={"BTC/USDT": "donchian_breakout"},
        starting_equity=10_000,
    )
    state.positions_by_symbol["BTC/USDT"] = PortfolioPosition(
        symbol="BTC/USDT",
        strategy="donchian_breakout",
        quantity=0,
        entry_price=100,
    )

    assert "INVALID_POSITION_QUANTITY:BTC/USDT" in reconcile_portfolio_state(state)

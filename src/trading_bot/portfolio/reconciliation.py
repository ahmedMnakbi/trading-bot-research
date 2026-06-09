from __future__ import annotations

from trading_bot.portfolio.portfolio_state import PortfolioPaperState


def reconcile_portfolio_state(state: PortfolioPaperState) -> list[str]:
    warnings: list[str] = []
    if state.cash < 0:
        warnings.append("NEGATIVE_CASH")
    for symbol, position in state.positions_by_symbol.items():
        if position.quantity <= 0:
            warnings.append(f"INVALID_POSITION_QUANTITY:{symbol}")
        if position.symbol != symbol:
            warnings.append(f"POSITION_SYMBOL_MISMATCH:{symbol}")
    return warnings

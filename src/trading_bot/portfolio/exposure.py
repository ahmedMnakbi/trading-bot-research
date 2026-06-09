from __future__ import annotations

from datetime import datetime
from typing import Any

from trading_bot.portfolio.portfolio_state import PortfolioPaperState


def calculate_exposure_snapshot(
    state: PortfolioPaperState,
    *,
    timestamp: datetime,
    mark_prices: dict[str, float],
) -> dict[str, Any]:
    symbol_exposures: dict[str, float] = {}
    strategy_exposures: dict[str, float] = {}
    for symbol, position in state.positions_by_symbol.items():
        value = position.market_value(mark_prices.get(symbol))
        symbol_exposures[symbol] = value
        strategy_exposures[position.strategy] = strategy_exposures.get(position.strategy, 0) + value

    gross_exposure = sum(abs(value) for value in symbol_exposures.values())
    net_exposure = sum(symbol_exposures.values())
    equity = state.equity or state.starting_equity
    largest_symbol = max(symbol_exposures.values(), default=0)
    largest_strategy = max(strategy_exposures.values(), default=0)
    return {
        "timestamp": timestamp,
        "cash": state.cash,
        "equity": state.equity,
        "gross_exposure": gross_exposure,
        "gross_exposure_pct": _pct(gross_exposure, equity),
        "net_exposure": net_exposure,
        "net_exposure_pct": _pct(net_exposure, equity),
        "symbol_exposures": symbol_exposures,
        "symbol_exposure_pct": {
            symbol: _pct(value, equity) for symbol, value in symbol_exposures.items()
        },
        "strategy_exposures": strategy_exposures,
        "strategy_exposure_pct": {
            strategy: _pct(value, equity) for strategy, value in strategy_exposures.items()
        },
        "open_position_count": len(state.positions_by_symbol),
        "largest_symbol_exposure_pct": _pct(largest_symbol, equity),
        "largest_strategy_exposure_pct": _pct(largest_strategy, equity),
    }


def _pct(value: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return value / denominator * 100

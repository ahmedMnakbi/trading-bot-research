from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class PortfolioPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    strategy: str
    quantity: float
    entry_price: float
    stop_loss: float | None = None
    take_profit: float | None = None

    def market_value(self, price: float | None = None) -> float:
        return self.quantity * (price if price is not None else self.entry_price)


class PortfolioPaperState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    portfolio_paper_run_id: str
    created_at: datetime
    updated_at: datetime
    exchange: str
    timeframe: str
    symbols: list[str]
    strategy_map: dict[str, str]
    starting_equity: float
    cash: float
    equity: float
    realized_pnl: float = 0
    unrealized_pnl: float = 0
    fees_paid: float = 0
    slippage_paid_estimate: float = 0
    positions_by_symbol: dict[str, PortfolioPosition] = Field(default_factory=dict)
    orders: list[dict[str, Any]] = Field(default_factory=list)
    trades: list[dict[str, Any]] = Field(default_factory=list)
    equity_curve: list[dict[str, Any]] = Field(default_factory=list)
    exposure_snapshots: list[dict[str, Any]] = Field(default_factory=list)
    last_processed_candle_by_symbol: dict[str, datetime | None] = Field(default_factory=dict)
    kill_switch_active: bool = False
    consecutive_data_errors_by_symbol: dict[str, int] = Field(default_factory=dict)
    consecutive_order_errors: int = 0
    portfolio_warnings: list[str] = Field(default_factory=list)


def new_portfolio_paper_state(
    *,
    exchange: str,
    timeframe: str,
    symbols: list[str],
    strategy_map: dict[str, str],
    starting_equity: float,
    portfolio_paper_run_id: str | None = None,
) -> PortfolioPaperState:
    now = datetime.now(UTC)
    return PortfolioPaperState(
        portfolio_paper_run_id=portfolio_paper_run_id
        or f"portfolio_paper_{now.strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}",
        created_at=now,
        updated_at=now,
        exchange=exchange,
        timeframe=timeframe,
        symbols=symbols,
        strategy_map=strategy_map,
        starting_equity=starting_equity,
        cash=starting_equity,
        equity=starting_equity,
        last_processed_candle_by_symbol={symbol: None for symbol in symbols},
        consecutive_data_errors_by_symbol={symbol: 0 for symbol in symbols},
    )

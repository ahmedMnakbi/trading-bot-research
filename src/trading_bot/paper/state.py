from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class PaperPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    quantity: float
    entry_price: float
    stop_loss: float | None = None
    take_profit: float | None = None


class PaperState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_run_id: str
    created_at: datetime
    updated_at: datetime
    exchange: str
    symbol: str
    timeframe: str
    strategy: str
    starting_equity: float
    cash: float
    equity: float
    open_position: PaperPosition | None = None
    realized_pnl: float = 0
    unrealized_pnl: float = 0
    fees_paid: float = 0
    slippage_paid_estimate: float = 0
    orders: list[dict[str, Any]] = Field(default_factory=list)
    trades: list[dict[str, Any]] = Field(default_factory=list)
    equity_curve: list[dict[str, Any]] = Field(default_factory=list)
    last_processed_candle_timestamp: datetime | None = None
    kill_switch_active: bool = False
    consecutive_data_errors: int = 0
    consecutive_order_errors: int = 0


def new_paper_state(
    *,
    exchange: str,
    symbol: str,
    timeframe: str,
    strategy: str,
    starting_equity: float,
    paper_run_id: str | None = None,
) -> PaperState:
    now = datetime.now(UTC)
    return PaperState(
        paper_run_id=paper_run_id or f"paper_{now.strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}",
        created_at=now,
        updated_at=now,
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        strategy=strategy,
        starting_equity=starting_equity,
        cash=starting_equity,
        equity=starting_equity,
    )


from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import pandas as pd


def max_drawdown_pct(equity_curve: pd.DataFrame) -> float:
    if equity_curve.empty:
        return 0.0
    running_max = equity_curve["equity"].cummax()
    drawdowns = (equity_curve["equity"] - running_max) / running_max * 100
    return abs(float(drawdowns.min()))


def consecutive_losses(trades: pd.DataFrame) -> int:
    max_losses = 0
    current = 0
    if trades.empty or "pnl" not in trades:
        return 0
    for pnl in trades["pnl"]:
        if pnl < 0:
            current += 1
            max_losses = max(max_losses, current)
        else:
            current = 0
    return max_losses


def profit_factor(trades: pd.DataFrame) -> float:
    if trades.empty or "pnl" not in trades:
        return 0.0
    gross_profit = float(trades.loc[trades["pnl"] > 0, "pnl"].sum())
    gross_loss = abs(float(trades.loc[trades["pnl"] < 0, "pnl"].sum()))
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def annualized_return_pct(
    equity_curve: pd.DataFrame, *, starting_equity: float, final_equity: float
) -> float | None:
    if len(equity_curve) < 2:
        return None
    first = equity_curve["timestamp"].iloc[0]
    last = equity_curve["timestamp"].iloc[-1]
    if not isinstance(first, datetime) or not isinstance(last, datetime):
        return None
    days = (last - first).total_seconds() / 86_400
    if days <= 0:
        return None
    return ((final_equity / starting_equity) ** (365 / days) - 1) * 100


def calculate_metrics(
    *,
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    orders: pd.DataFrame,
    starting_equity: float,
) -> dict[str, Any]:
    final_equity = (
        float(equity_curve["equity"].iloc[-1]) if not equity_curve.empty else starting_equity
    )
    wins = trades.loc[trades["pnl"] > 0, "pnl"] if not trades.empty else pd.Series(dtype=float)
    losses = trades.loc[trades["pnl"] < 0, "pnl"] if not trades.empty else pd.Series(dtype=float)
    filled_orders = orders[orders["status"] == "FILLED"] if not orders.empty else orders
    exposure_time_pct = 0.0
    if not equity_curve.empty and "in_position" in equity_curve:
        exposure_time_pct = float(equity_curve["in_position"].mean() * 100)
    return {
        "total_return_pct": (final_equity / starting_equity - 1) * 100,
        "annualized_return_pct": annualized_return_pct(
            equity_curve, starting_equity=starting_equity, final_equity=final_equity
        ),
        "max_drawdown_pct": max_drawdown_pct(equity_curve),
        "win_rate_pct": float(len(wins) / len(trades) * 100) if len(trades) else 0.0,
        "profit_factor": profit_factor(trades),
        "number_of_trades": int(len(trades)),
        "average_win": float(wins.mean()) if len(wins) else 0.0,
        "average_loss": float(losses.mean()) if len(losses) else 0.0,
        "largest_win": float(wins.max()) if len(wins) else 0.0,
        "largest_loss": float(losses.min()) if len(losses) else 0.0,
        "consecutive_losses": consecutive_losses(trades),
        "fees_paid": float(filled_orders["fee"].sum()) if not filled_orders.empty else 0.0,
        "slippage_paid_estimate": (
            float(filled_orders["slippage_paid_estimate"].sum())
            if not filled_orders.empty
            else 0.0
        ),
        "exposure_time_pct": exposure_time_pct,
        "final_equity": final_equity,
    }


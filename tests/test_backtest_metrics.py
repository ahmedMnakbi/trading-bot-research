from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from trading_bot.backtesting.metrics import calculate_metrics, max_drawdown_pct, profit_factor


def test_metrics_calculate_max_drawdown_correctly() -> None:
    curve = pd.DataFrame(
        {
            "timestamp": [
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 2, tzinfo=UTC),
                datetime(2024, 1, 3, tzinfo=UTC),
            ],
            "equity": [100, 120, 90],
        }
    )

    assert max_drawdown_pct(curve) == 25


def test_metrics_calculate_profit_factor_correctly() -> None:
    trades = pd.DataFrame({"pnl": [100, -50, 50]})

    assert profit_factor(trades) == 3


def test_metrics_handle_zero_trades_without_crashing() -> None:
    curve = pd.DataFrame(
        {"timestamp": [datetime(2024, 1, 1, tzinfo=UTC)], "equity": [100], "in_position": [False]}
    )
    trades = pd.DataFrame(columns=["pnl"])
    orders = pd.DataFrame(columns=["status", "fee", "slippage_paid_estimate"])

    metrics = calculate_metrics(
        equity_curve=curve,
        trades=trades,
        orders=orders,
        starting_equity=100,
    )

    assert metrics["number_of_trades"] == 0
    assert metrics["profit_factor"] == 0
    assert metrics["final_equity"] == 100


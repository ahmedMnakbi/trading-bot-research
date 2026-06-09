from __future__ import annotations

from typing import Any


def compare_to_benchmark(
    *, strategy_metrics: dict[str, Any], benchmark_metrics: dict[str, Any]
) -> dict[str, Any]:
    return {
        "strategy_total_return_pct": strategy_metrics["total_return_pct"],
        "benchmark_total_return_pct": benchmark_metrics["total_return_pct"],
        "excess_return_pct": (
            strategy_metrics["total_return_pct"] - benchmark_metrics["total_return_pct"]
        ),
        "strategy_max_drawdown_pct": strategy_metrics["max_drawdown_pct"],
        "benchmark_max_drawdown_pct": benchmark_metrics["max_drawdown_pct"],
        "drawdown_difference_pct": (
            strategy_metrics["max_drawdown_pct"] - benchmark_metrics["max_drawdown_pct"]
        ),
        "strategy_profit_factor": strategy_metrics["profit_factor"],
        "benchmark_profit_factor": benchmark_metrics["profit_factor"],
        "strategy_trade_count": strategy_metrics["number_of_trades"],
        "benchmark_trade_count": benchmark_metrics["number_of_trades"],
    }


def warning_flags(
    *,
    train_metrics: dict[str, Any],
    test_metrics: dict[str, Any],
    buy_and_hold_metrics: dict[str, Any] | None = None,
) -> list[str]:
    flags: list[str] = []
    test_trades = int(test_metrics.get("number_of_trades", 0))
    if test_trades == 0:
        flags.append("ZERO_TRADES")
    if test_trades < 10:
        flags.append("TOO_FEW_TRADES")
    train_return = float(train_metrics.get("total_return_pct", 0))
    test_return = float(test_metrics.get("total_return_pct", 0))
    if train_return > 0 and test_return < train_return * 0.5:
        flags.append("TEST_RETURN_COLLAPSE")
    if float(test_metrics.get("max_drawdown_pct", 0)) > float(
        train_metrics.get("max_drawdown_pct", 0)
    ):
        flags.append("TEST_DRAWDOWN_WORSE_THAN_TRAIN")
    if buy_and_hold_metrics and test_return < float(buy_and_hold_metrics["total_return_pct"]):
        flags.append("UNDERPERFORMS_BUY_AND_HOLD")
    if float(test_metrics.get("max_drawdown_pct", 0)) > 25:
        flags.append("HIGH_DRAWDOWN")
    if (
        float(train_metrics.get("profit_factor", 0)) > 1.5
        and float(test_metrics.get("profit_factor", 0)) < 1.0
    ):
        flags.append("PROFIT_FACTOR_UNSTABLE")
    return flags

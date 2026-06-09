from __future__ import annotations

from statistics import mean, median
from typing import Any

from trading_bot.validation.models import WalkForwardWindow


def create_walk_forward_windows(
    total_bars: int,
    *,
    train_bars: int,
    test_bars: int,
    step_bars: int,
) -> list[WalkForwardWindow]:
    if min(train_bars, test_bars, step_bars) <= 0:
        raise ValueError("walk-forward bars must be positive")
    windows: list[WalkForwardWindow] = []
    start = 0
    index = 1
    while start + train_bars + test_bars <= total_bars:
        windows.append(
            WalkForwardWindow(
                train_start=start,
                train_end=start + train_bars,
                test_start=start + train_bars,
                test_end=start + train_bars + test_bars,
                index=index,
            )
        )
        start += step_bars
        index += 1
    if not windows:
        raise ValueError("insufficient bars for walk-forward windows")
    return windows


def aggregate_walk_forward_metrics(window_results: list[dict[str, Any]]) -> dict[str, Any]:
    if not window_results:
        raise ValueError("empty walk-forward result set")
    returns = [float(result["test_metrics"]["total_return_pct"]) for result in window_results]
    drawdowns = [float(result["test_metrics"]["max_drawdown_pct"]) for result in window_results]
    profit_factors = [float(result["test_metrics"]["profit_factor"]) for result in window_results]
    trades = [int(result["test_metrics"]["number_of_trades"]) for result in window_results]
    positive = sum(1 for value in returns if value > 0)
    number = len(window_results)
    return {
        "number_of_windows": number,
        "positive_test_windows": positive,
        "negative_test_windows": number - positive,
        "median_test_return_pct": median(returns),
        "mean_test_return_pct": mean(returns),
        "worst_test_drawdown_pct": max(drawdowns) if drawdowns else 0.0,
        "median_profit_factor": median(profit_factors),
        "total_test_trades": sum(trades),
        "consistency_score": positive / number,
    }


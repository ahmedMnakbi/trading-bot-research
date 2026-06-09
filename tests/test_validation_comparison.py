from __future__ import annotations

from trading_bot.validation.comparison import compare_to_benchmark, warning_flags


def metrics(**overrides):  # type: ignore[no-untyped-def]
    base = {
        "total_return_pct": 0,
        "max_drawdown_pct": 0,
        "profit_factor": 0,
        "number_of_trades": 0,
    }
    base.update(overrides)
    return base


def test_benchmark_comparison_calculates_excess_return() -> None:
    comparison = compare_to_benchmark(
        strategy_metrics=metrics(total_return_pct=10),
        benchmark_metrics=metrics(total_return_pct=3),
    )

    assert comparison["excess_return_pct"] == 7


def test_benchmark_comparison_includes_drawdown_difference() -> None:
    comparison = compare_to_benchmark(
        strategy_metrics=metrics(max_drawdown_pct=12),
        benchmark_metrics=metrics(max_drawdown_pct=8),
    )

    assert comparison["drawdown_difference_pct"] == 4


def test_warning_flag_triggers_on_zero_trades() -> None:
    flags = warning_flags(train_metrics=metrics(), test_metrics=metrics())

    assert "ZERO_TRADES" in flags


def test_warning_flag_triggers_on_too_few_trades() -> None:
    flags = warning_flags(train_metrics=metrics(), test_metrics=metrics(number_of_trades=3))

    assert "TOO_FEW_TRADES" in flags


def test_warning_flag_triggers_when_strategy_underperforms_buy_and_hold() -> None:
    flags = warning_flags(
        train_metrics=metrics(),
        test_metrics=metrics(total_return_pct=1, number_of_trades=20),
        buy_and_hold_metrics=metrics(total_return_pct=5),
    )

    assert "UNDERPERFORMS_BUY_AND_HOLD" in flags


def test_warning_flag_triggers_on_high_drawdown() -> None:
    flags = warning_flags(
        train_metrics=metrics(),
        test_metrics=metrics(max_drawdown_pct=30, number_of_trades=20),
    )

    assert "HIGH_DRAWDOWN" in flags

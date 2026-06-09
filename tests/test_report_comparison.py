from __future__ import annotations

from trading_bot.reporting.comparison import compare_paper_to_references


def test_comparison_calculates_degradation_versus_validation() -> None:
    result = compare_paper_to_references(
        paper_metrics={
            "total_return_pct": 5,
            "max_drawdown_pct": 7,
            "profit_factor": 1,
            "number_of_trades": 3,
        },
        validation_metrics={
            "total_return_pct": 12,
            "max_drawdown_pct": 4,
            "profit_factor": 2,
            "number_of_trades": 4,
        },
    )

    assert result["return_degradation_vs_validation_pct"] == 7


def test_comparison_calculates_degradation_versus_backtest() -> None:
    result = compare_paper_to_references(
        paper_metrics={
            "total_return_pct": 5,
            "max_drawdown_pct": 7,
            "profit_factor": 1,
            "number_of_trades": 3,
        },
        backtest_metrics={
            "total_return_pct": 9,
            "max_drawdown_pct": 4,
            "profit_factor": 2,
            "number_of_trades": 4,
        },
    )

    assert result["return_degradation_vs_backtest_pct"] == 4

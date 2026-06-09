from __future__ import annotations

from typing import Any


def compare_paper_to_references(
    *,
    paper_metrics: dict[str, Any],
    validation_metrics: dict[str, Any] | None = None,
    backtest_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "paper_total_return_pct": paper_metrics.get("total_return_pct"),
        "paper_max_drawdown_pct": paper_metrics.get("max_drawdown_pct"),
        "paper_profit_factor": paper_metrics.get("profit_factor"),
        "paper_trade_count": paper_metrics.get("number_of_trades"),
        "warnings": [],
    }
    if validation_metrics:
        summary.update(
            {
                "validation_test_return_pct": validation_metrics.get("total_return_pct"),
                "validation_test_max_drawdown_pct": validation_metrics.get("max_drawdown_pct"),
                "validation_test_profit_factor": validation_metrics.get("profit_factor"),
                "validation_trade_count": validation_metrics.get("number_of_trades"),
                "return_degradation_vs_validation_pct": _degradation(
                    validation_metrics.get("total_return_pct"),
                    paper_metrics.get("total_return_pct"),
                ),
                "drawdown_worsening_vs_validation_pct": _worsening(
                    validation_metrics.get("max_drawdown_pct"),
                    paper_metrics.get("max_drawdown_pct"),
                ),
            }
        )
    else:
        summary["warnings"].append("missing_validation_comparison")
    if backtest_metrics:
        summary.update(
            {
                "backtest_total_return_pct": backtest_metrics.get("total_return_pct"),
                "backtest_max_drawdown_pct": backtest_metrics.get("max_drawdown_pct"),
                "backtest_profit_factor": backtest_metrics.get("profit_factor"),
                "backtest_trade_count": backtest_metrics.get("number_of_trades"),
                "return_degradation_vs_backtest_pct": _degradation(
                    backtest_metrics.get("total_return_pct"), paper_metrics.get("total_return_pct")
                ),
                "drawdown_worsening_vs_backtest_pct": _worsening(
                    backtest_metrics.get("max_drawdown_pct"), paper_metrics.get("max_drawdown_pct")
                ),
            }
        )
    else:
        summary["warnings"].append("missing_backtest_comparison")
    return summary


def _degradation(reference: Any, observed: Any) -> float | None:
    if reference is None or observed is None:
        return None
    return float(reference) - float(observed)


def _worsening(reference: Any, observed: Any) -> float | None:
    if reference is None or observed is None:
        return None
    return float(observed) - float(reference)

from __future__ import annotations

from typing import Any

HIGH_SEVERITY_WARNINGS = {
    "ZERO_TRADES",
    "HIGH_DRAWDOWN",
    "PROFIT_FACTOR_UNSTABLE",
    "UNDERPERFORMS_BUY_AND_HOLD",
}


def label_candidate(metrics: dict[str, Any], gates: Any) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if metrics.get("number_of_failed_stages", 0) > 0:
        return "REJECTED", ["stage_failed"]
    if metrics.get("validation_total_test_trades", 0) == 0:
        return "REJECTED", ["zero_validation_trades"]
    if (
        metrics.get("validation_worst_test_drawdown_pct") is not None
        and metrics["validation_worst_test_drawdown_pct"] > gates.max_validation_drawdown_pct
    ):
        return "REJECTED", ["validation_drawdown_exceeded"]
    warnings = set(metrics.get("validation_warning_flags") or [])
    if gates.require_no_high_severity_warnings and warnings.intersection(HIGH_SEVERITY_WARNINGS):
        return "REJECTED", ["high_severity_warning"]
    if metrics.get("validation_number_of_windows", 0) < gates.min_validation_windows:
        reasons.append("too_few_validation_windows")
    if metrics.get("validation_total_test_trades", 0) < gates.min_total_test_trades:
        reasons.append("too_few_test_trades")
    if metrics.get("excess_return_vs_buy_and_hold_pct") is None:
        reasons.append("missing_benchmark_comparison")
    elif (
        metrics["excess_return_vs_buy_and_hold_pct"]
        < -gates.max_underperformance_vs_buy_and_hold_pct
    ):
        return "REJECTED", ["underperforms_buy_and_hold"]
    if (
        gates.require_positive_consistency_score
        and metrics.get("validation_consistency_score", 0) <= 0
    ):
        reasons.append("non_positive_consistency_score")
    if reasons:
        return "NEEDS_MORE_DATA", reasons
    return "PAPER_TRADING_CANDIDATE", ["passed_configured_campaign_review_gates"]

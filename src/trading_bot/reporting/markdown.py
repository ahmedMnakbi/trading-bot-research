from __future__ import annotations

LIMITATIONS = (
    "Paper trading uses simulated fills and does not guarantee live execution quality or "
    "profitability. This report is not approval for real-money trading. Human approval is "
    "still required before any live deployment."
)


def render_markdown_report(
    *,
    metadata: dict[str, object],
    paper_summary: dict[str, object],
    metrics: dict[str, object],
    health: dict[str, object],
    readiness: dict[str, object],
    comparison: dict[str, object],
    warnings: list[str],
) -> str:
    status = readiness["status"]
    return "\n".join(
        [
            "# Paper Trading Report",
            "",
            "## Run Metadata",
            f"- Paper run: {metadata.get('paper_run_id')}",
            f"- Report run: {metadata.get('report_run_id')}",
            "",
            "## Paper Performance Summary",
            f"- Final equity: {metrics.get('final_equity')}",
            f"- Total return pct: {metrics.get('total_return_pct')}",
            f"- Trades: {metrics.get('number_of_trades')}",
            "",
            "## Health and Alert Summary",
            f"- Total health events: {health.get('total_health_events')}",
            f"- Total alerts: {health.get('total_alerts')}",
            f"- Kill switch active: {health.get('kill_switch_active')}",
            "",
            "## Readiness Gate Results",
            f"- Status: {status}",
            f"- Failed gates: {readiness.get('failed_gates')}",
            f"- Needs more: {readiness.get('needs_more_gates')}",
            "",
            "## Backtest/Validation Comparison",
            f"- Comparison: {comparison}",
            "",
            "## Warnings",
            "\n".join(f"- {warning}" for warning in warnings) if warnings else "- None",
            "",
            "## Decision",
            str(status),
            "",
            "## Important Limitations",
            LIMITATIONS,
        ]
    )


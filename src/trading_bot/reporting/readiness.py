from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ReadinessStatus = Literal["NOT_READY", "NEEDS_MORE_PAPER_TRADING", "ELIGIBLE_FOR_HUMAN_REVIEW"]


@dataclass(frozen=True)
class ReadinessConfig:
    min_paper_runtime_days: int
    min_paper_trades: int
    max_paper_drawdown_pct: float
    max_daily_loss_pct: float
    max_weekly_loss_pct: float
    max_unresolved_alerts: int
    require_no_kill_switch: bool
    require_no_state_corruption: bool
    require_validation_reference: bool
    require_human_approval_for_live: bool


def evaluate_readiness(
    *,
    metrics: dict[str, Any],
    health: dict[str, Any],
    metadata: dict[str, Any],
    validation_run_id: str | None,
    config: ReadinessConfig,
) -> dict[str, Any]:
    failed: list[str] = []
    needs_more: list[str] = []
    if metadata.get("live_trading") is True:
        failed.append("live_trading_enabled")
    if metadata.get("real_orders_enabled") is True:
        failed.append("real_orders_enabled")
    if metadata.get("uses_private_api") is True:
        failed.append("private_api_usage")
    if config.require_no_state_corruption and health.get("state_corruption_detected"):
        failed.append("state_corruption")
    if config.require_no_kill_switch and health.get("kill_switch_active"):
        failed.append("kill_switch_active")
    if (
        metrics.get("max_drawdown_pct") is not None
        and metrics["max_drawdown_pct"] > config.max_paper_drawdown_pct
    ):
        failed.append("drawdown_limit_exceeded")
    if (
        metrics.get("max_daily_loss_pct") is not None
        and abs(metrics["max_daily_loss_pct"]) > config.max_daily_loss_pct
    ):
        failed.append("daily_loss_limit_exceeded")
    if (
        metrics.get("max_weekly_loss_pct") is not None
        and abs(metrics["max_weekly_loss_pct"]) > config.max_weekly_loss_pct
    ):
        failed.append("weekly_loss_limit_exceeded")
    if health.get("unresolved_alerts", 0) > config.max_unresolved_alerts:
        failed.append("unresolved_alerts")
    if config.require_validation_reference and validation_run_id is None:
        failed.append("missing_validation_reference")
    if config.require_human_approval_for_live is not True:
        failed.append("human_approval_not_required")
    if (
        metrics.get("runtime_days") is None
        or metrics["runtime_days"] < config.min_paper_runtime_days
    ):
        needs_more.append("minimum_runtime_not_met")
    if (
        metrics.get("number_of_trades") is None
        or metrics["number_of_trades"] < config.min_paper_trades
    ):
        needs_more.append("minimum_trade_count_not_met")
    sparse = metrics.get("number_of_trades") in {None, 0}
    if sparse:
        needs_more.append("metrics_too_sparse")

    if failed:
        status: ReadinessStatus = "NOT_READY"
    elif needs_more:
        status = "NEEDS_MORE_PAPER_TRADING"
    else:
        status = "ELIGIBLE_FOR_HUMAN_REVIEW"
    return {"status": status, "failed_gates": failed, "needs_more_gates": needs_more}

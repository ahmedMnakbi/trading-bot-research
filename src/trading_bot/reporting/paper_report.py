from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from trading_bot.backtesting.metrics import consecutive_losses, max_drawdown_pct, profit_factor
from trading_bot.config.settings import ReadinessSettings
from trading_bot.paper.state import PaperState
from trading_bot.reporting.artifacts import write_report_artifacts
from trading_bot.reporting.comparison import compare_paper_to_references
from trading_bot.reporting.html import render_html_report
from trading_bot.reporting.markdown import render_markdown_report
from trading_bot.reporting.readiness import ReadinessConfig, evaluate_readiness


class PaperReportError(RuntimeError):
    """Raised when a paper report cannot be generated."""


def generate_paper_report(
    *,
    paper_run_dir: str | Path,
    output_root: str | Path,
    config_snapshot: dict[str, Any],
    readiness_settings: ReadinessSettings,
    validation_run_dir: str | Path | None = None,
    backtest_run_dir: str | Path | None = None,
    report_run_id: str | None = None,
) -> Path:
    paper_dir = Path(paper_run_dir)
    if not paper_dir.exists():
        raise PaperReportError(f"missing paper run directory: {paper_dir}")
    selected_report_run_id = (
        report_run_id or f"report_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}"
    )
    output_dir = Path(output_root) / selected_report_run_id
    state, state_corrupt = _load_state(paper_dir)
    run_metadata = _read_json(paper_dir / "run_metadata.json")
    orders = _read_parquet(paper_dir / "orders.parquet")
    trades = _read_parquet(paper_dir / "trades.parquet")
    equity = _read_parquet(paper_dir / "equity_curve.parquet")
    metrics = compute_paper_metrics(state=state, orders=orders, trades=trades, equity_curve=equity)
    health = summarize_health(paper_dir=paper_dir, state=state, state_corruption=state_corrupt)
    validation_metrics = _load_validation_metrics(validation_run_dir)
    backtest_metrics = _load_backtest_metrics(backtest_run_dir)
    comparison = compare_paper_to_references(
        paper_metrics=metrics,
        validation_metrics=validation_metrics,
        backtest_metrics=backtest_metrics,
    )
    metadata = {
        "report_run_id": selected_report_run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "paper_run_id": paper_dir.name,
        "validation_run_id": Path(validation_run_dir).name if validation_run_dir else None,
        "backtest_run_id": Path(backtest_run_dir).name if backtest_run_dir else None,
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
        "human_approval_required_for_live": readiness_settings.require_human_approval_for_live,
    }
    readiness = evaluate_readiness(
        metrics=metrics,
        health=health,
        metadata={**metadata, **run_metadata},
        validation_run_id=metadata["validation_run_id"],
        config=ReadinessConfig(
            min_paper_runtime_days=readiness_settings.min_paper_runtime_days,
            min_paper_trades=readiness_settings.min_paper_trades,
            max_paper_drawdown_pct=readiness_settings.max_paper_drawdown_pct,
            max_daily_loss_pct=readiness_settings.max_daily_loss_pct,
            max_weekly_loss_pct=readiness_settings.max_weekly_loss_pct,
            max_unresolved_alerts=readiness_settings.max_unresolved_alerts,
            require_no_kill_switch=readiness_settings.require_no_kill_switch,
            require_no_state_corruption=readiness_settings.require_no_state_corruption,
            require_validation_reference=readiness_settings.require_validation_reference,
            require_human_approval_for_live=readiness_settings.require_human_approval_for_live,
        ),
    )
    warnings = _warnings(metrics=metrics, health=health, comparison=comparison)
    paper_summary = {
        "paper_run_id": paper_dir.name,
        "strategy": state.strategy if state else run_metadata.get("strategy"),
        "final_equity": metrics["final_equity"],
        "status": readiness["status"],
    }
    markdown = render_markdown_report(
        metadata=metadata,
        paper_summary=paper_summary,
        metrics=metrics,
        health=health,
        readiness=readiness,
        comparison=comparison,
        warnings=warnings,
    )
    html = render_html_report(
        readiness=readiness, metrics=metrics, health=health, warnings=warnings
    )
    return write_report_artifacts(
        output_dir=output_dir,
        config_snapshot=config_snapshot,
        artifacts={
            "paper_summary.json": paper_summary,
            "paper_metrics.json": metrics,
            "readiness_gates.json": readiness,
            "health_summary.json": health,
            "alert_summary.json": _alert_summary(paper_dir),
            "comparison_summary.json": comparison,
            "report.md": markdown,
            "report.html": html,
            "run_metadata.json": metadata,
        },
    )


def compute_paper_metrics(
    *,
    state: PaperState | None,
    orders: pd.DataFrame,
    trades: pd.DataFrame,
    equity_curve: pd.DataFrame,
) -> dict[str, Any]:
    starting_equity = state.starting_equity if state else _first_equity(equity_curve)
    final_equity = state.equity if state else _last_equity(equity_curve, starting_equity)
    wins = (
        trades.loc[trades["pnl"] > 0, "pnl"]
        if not trades.empty and "pnl" in trades
        else pd.Series(dtype=float)
    )
    losses = (
        trades.loc[trades["pnl"] < 0, "pnl"]
        if not trades.empty and "pnl" in trades
        else pd.Series(dtype=float)
    )
    daily = _daily_returns(equity_curve)
    weekly = _weekly_returns(equity_curve)
    return {
        "starting_equity": starting_equity,
        "final_equity": final_equity,
        "total_return_pct": _pct(final_equity, starting_equity),
        "realized_pnl": state.realized_pnl if state else None,
        "unrealized_pnl": state.unrealized_pnl if state else None,
        "max_drawdown_pct": max_drawdown_pct(equity_curve) if not equity_curve.empty else None,
        "number_of_trades": int(len(trades)),
        "win_rate_pct": float(len(wins) / len(trades) * 100) if len(trades) else None,
        "profit_factor": profit_factor(trades) if len(trades) else None,
        "average_win": float(wins.mean()) if len(wins) else None,
        "average_loss": float(losses.mean()) if len(losses) else None,
        "largest_win": float(wins.max()) if len(wins) else None,
        "largest_loss": float(losses.min()) if len(losses) else None,
        "consecutive_losses": consecutive_losses(trades) if len(trades) else None,
        "fees_paid": state.fees_paid if state else _sum_col(orders, "fee"),
        "slippage_paid_estimate": (
            state.slippage_paid_estimate if state else _sum_col(orders, "slippage_paid_estimate")
        ),
        "exposure_time_pct": _exposure_time_pct(equity_curve, state),
        "average_trade_duration": None,
        "daily_returns": daily,
        "best_day_pct": max(daily) if daily else None,
        "worst_day_pct": min(daily) if daily else None,
        "max_daily_loss_pct": _max_loss(daily),
        "max_weekly_loss_pct": _max_loss(weekly),
        "open_position_count": 1 if state and state.open_position else 0,
        "runtime_days": _runtime_days(state),
    }


def summarize_health(
    *, paper_dir: Path, state: PaperState | None, state_corruption: bool
) -> dict[str, Any]:
    health_events = _read_jsonl(paper_dir / "health_events.jsonl")
    alerts = _read_jsonl(paper_dir / "alerts.jsonl")
    codes = [event.get("code") for event in health_events]
    return {
        "total_health_events": len(health_events),
        "total_alerts": len(alerts),
        "unresolved_alerts": len(alerts),
        "kill_switch_active": bool(state.kill_switch_active) if state else False,
        "state_corruption_detected": state_corruption,
        "data_stale_events": codes.count("DATA_STALE"),
        "data_gap_events": codes.count("DATA_GAP_DETECTED"),
        "strategy_errors": codes.count("STRATEGY_ERROR"),
        "risk_rejections": codes.count("RISK_REJECTED"),
        "order_rejections": codes.count("ORDER_REJECTED"),
        "state_write_failures": codes.count("STATE_WRITE_FAILED"),
    }


def _load_state(paper_dir: Path) -> tuple[PaperState | None, bool]:
    path = paper_dir / "state.json"
    if not path.exists():
        return None, True
    try:
        return PaperState.model_validate_json(path.read_text(encoding="utf-8")), False
    except Exception:
        return None, True


def _read_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_parquet(path)
    except Exception:
        return pd.DataFrame()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                rows.append({"code": "MALFORMED"})
    return rows


def _alert_summary(paper_dir: Path) -> dict[str, Any]:
    alerts = _read_jsonl(paper_dir / "alerts.jsonl")
    return {"total_alerts": len(alerts), "unresolved_alerts": len(alerts)}


def _load_validation_metrics(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    data = _read_json(Path(path) / "static_split_results.json")
    for result in data.values():
        if isinstance(result, dict) and "test_metrics" in result:
            return result["test_metrics"]
    return None


def _load_backtest_metrics(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return _read_json(Path(path) / "metrics.json") or None


def _warnings(
    *, metrics: dict[str, Any], health: dict[str, Any], comparison: dict[str, Any]
) -> list[str]:
    warnings = list(comparison.get("warnings", []))
    if metrics.get("number_of_trades") == 0:
        warnings.append("metrics_sparse_zero_trades")
    if health.get("state_corruption_detected"):
        warnings.append("state_corruption_detected")
    return warnings


def _first_equity(equity: pd.DataFrame) -> float:
    return float(equity["equity"].iloc[0]) if not equity.empty and "equity" in equity else 0.0


def _last_equity(equity: pd.DataFrame, fallback: float) -> float:
    return float(equity["equity"].iloc[-1]) if not equity.empty and "equity" in equity else fallback


def _pct(final: float, initial: float) -> float | None:
    return (final / initial - 1) * 100 if initial else None


def _sum_col(frame: pd.DataFrame, column: str) -> float:
    return float(frame[column].sum()) if not frame.empty and column in frame else 0.0


def _daily_returns(equity: pd.DataFrame) -> list[float]:
    return _period_returns(equity, "D")


def _weekly_returns(equity: pd.DataFrame) -> list[float]:
    return _period_returns(equity, "W")


def _period_returns(equity: pd.DataFrame, period: str) -> list[float]:
    if equity.empty or "timestamp" not in equity or "equity" not in equity:
        return []
    series = equity.copy()
    series["timestamp"] = pd.to_datetime(series["timestamp"], utc=True)
    resampled = series.set_index("timestamp")["equity"].resample(period).last().dropna()
    return [float(value) for value in (resampled.pct_change().dropna() * 100)]


def _max_loss(returns: list[float]) -> float | None:
    if not returns:
        return None
    return abs(min(0.0, min(returns)))


def _exposure_time_pct(equity: pd.DataFrame, state: PaperState | None) -> float | None:
    if not equity.empty and "position_quantity" in equity:
        return float((equity["position_quantity"] > 0).mean() * 100)
    return 100.0 if state and state.open_position else 0.0


def _runtime_days(state: PaperState | None) -> float | None:
    if state is None:
        return None
    return (state.updated_at - state.created_at).total_seconds() / 86_400

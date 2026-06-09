from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
import yaml

from trading_bot.audit.integrity import write_artifact_manifest
from trading_bot.paper.store import PortfolioPaperStateStore

LIMITATIONS = (
    "Portfolio paper trading uses simulated fills and does not guarantee live execution quality, "
    "portfolio liquidity, or profitability. This report is not approval for real-money trading. "
    "Human approval remains mandatory before any live deployment."
)


class PortfolioPaperReportError(RuntimeError):
    """Raised when a portfolio paper report cannot be generated."""


def generate_portfolio_paper_report(
    *,
    state_dir: Path,
    output_root: Path,
    portfolio_paper_run_id: str,
    config_snapshot: dict[str, Any],
) -> Path:
    store = PortfolioPaperStateStore(state_dir)
    state = store.load(portfolio_paper_run_id)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    report_run_id = f"portfolio_report_{timestamp}_{uuid4().hex[:8]}"
    output_dir = output_root / report_run_id
    if output_dir.exists():
        raise PortfolioPaperReportError(f"output directory collision: {output_dir}")
    output_dir.mkdir(parents=True)

    summary = {
        "portfolio_paper_run_id": state.portfolio_paper_run_id,
        "symbols": state.symbols,
        "strategy_map": state.strategy_map,
        "starting_equity": state.starting_equity,
        "ending_equity": state.equity,
        "cash": state.cash,
        "open_positions": len(state.positions_by_symbol),
        "kill_switch_active": state.kill_switch_active,
    }
    metrics = {
        "total_return_pct": _pct(state.equity - state.starting_equity, state.starting_equity),
        "max_drawdown_pct": _max_drawdown(state.equity_curve, state.starting_equity),
        "number_of_trades": len(state.trades),
        "fees_paid": state.fees_paid,
        "slippage_paid_estimate": state.slippage_paid_estimate,
        "risk_rejections": _count_order_rejections(state.orders),
    }
    exposure_summary = _exposure_summary(state.exposure_snapshots)
    health_summary = _jsonl_summary(store.run_dir(portfolio_paper_run_id) / "health_events.jsonl")
    alert_summary = _jsonl_summary(store.run_dir(portfolio_paper_run_id) / "alerts.jsonl")
    readiness = {
        "eligible_for_human_review": False,
        "reason": "portfolio paper report is informational only",
        "live_trading_approved": False,
    }
    metadata = {
        "report_run_id": report_run_id,
        "portfolio_paper_run_id": state.portfolio_paper_run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
    }

    (output_dir / "config_snapshot.yaml").write_text(
        yaml.safe_dump(config_snapshot, sort_keys=False), encoding="utf-8"
    )
    _write_json(output_dir / "portfolio_summary.json", summary)
    _write_json(output_dir / "portfolio_metrics.json", metrics)
    _write_json(output_dir / "exposure_summary.json", exposure_summary)
    _write_json(output_dir / "health_summary.json", health_summary)
    _write_json(output_dir / "alert_summary.json", alert_summary)
    _write_json(output_dir / "readiness_gates.json", readiness)
    _write_json(output_dir / "run_metadata.json", metadata)
    markdown = _render_markdown(summary, metrics, exposure_summary, health_summary, alert_summary)
    (output_dir / "report.md").write_text(markdown, encoding="utf-8")
    (output_dir / "report.html").write_text(_render_html(markdown), encoding="utf-8")
    write_artifact_manifest(output_dir)
    return output_dir


def _render_markdown(
    summary: dict[str, Any],
    metrics: dict[str, Any],
    exposure: dict[str, Any],
    health: dict[str, Any],
    alerts: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# Portfolio Paper Trading Report",
            "",
            f"Portfolio run: `{summary['portfolio_paper_run_id']}`",
            f"Total return: {metrics['total_return_pct']:.4f}%",
            f"Max drawdown: {metrics['max_drawdown_pct']:.4f}%",
            f"Number of trades: {metrics['number_of_trades']}",
            f"Fees: {metrics['fees_paid']:.4f}",
            f"Slippage estimate: {metrics['slippage_paid_estimate']:.4f}",
            f"Open positions: {summary['open_positions']}",
            f"Largest symbol exposure: {exposure['largest_symbol_exposure_pct']:.4f}%",
            f"Largest strategy exposure: {exposure['largest_strategy_exposure_pct']:.4f}%",
            f"Risk rejections: {metrics['risk_rejections']}",
            f"Health events: {health['count']}",
            f"Alerts: {alerts['count']}",
            f"Kill switch active: {summary['kill_switch_active']}",
            "",
            "## Limitations",
            "",
            LIMITATIONS,
            "",
        ]
    )


def _render_html(markdown: str) -> str:
    body = "".join(f"<p>{line}</p>" for line in markdown.splitlines())
    return f"<!doctype html><html><body>{body}</body></html>"


def _exposure_summary(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    if not snapshots:
        return {
            "largest_symbol_exposure_pct": 0,
            "largest_strategy_exposure_pct": 0,
            "max_gross_exposure_pct": 0,
        }
    return {
        "largest_symbol_exposure_pct": max(
            float(item.get("largest_symbol_exposure_pct", 0)) for item in snapshots
        ),
        "largest_strategy_exposure_pct": max(
            float(item.get("largest_strategy_exposure_pct", 0)) for item in snapshots
        ),
        "max_gross_exposure_pct": max(
            float(item.get("gross_exposure_pct", 0)) for item in snapshots
        ),
    }


def _jsonl_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"count": 0, "codes": {}}
    codes: dict[str, int] = {}
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        count += 1
        payload = json.loads(line)
        code = str(payload.get("code", "UNKNOWN"))
        codes[code] = codes.get(code, 0) + 1
    return {"count": count, "codes": codes}


def _count_order_rejections(orders: list[dict[str, Any]]) -> int:
    return sum(1 for order in orders if order.get("status") == "rejected")


def _max_drawdown(equity_curve: list[dict[str, Any]], starting_equity: float) -> float:
    values = [starting_equity]
    values.extend(float(item["equity"]) for item in equity_curve if "equity" in item)
    peak = values[0]
    max_drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        max_drawdown = max(max_drawdown, _pct(peak - value, peak))
    return max_drawdown


def _pct(value: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return value / denominator * 100


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Path):
        return os.fspath(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value

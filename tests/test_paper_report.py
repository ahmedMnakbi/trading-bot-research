from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from trading_bot.config.settings import ReadinessSettings
from trading_bot.paper.state import new_paper_state
from trading_bot.paper.store import PaperStateStore
from trading_bot.reporting.markdown import LIMITATIONS
from trading_bot.reporting.paper_report import generate_paper_report, summarize_health


def readiness(**overrides):  # type: ignore[no-untyped-def]
    data = {
        "enabled": True,
        "min_paper_runtime_days": 0,
        "min_paper_trades": 0,
        "max_paper_drawdown_pct": 10,
        "max_daily_loss_pct": 1,
        "max_weekly_loss_pct": 3,
        "max_unresolved_alerts": 99,
        "require_no_kill_switch": True,
        "require_no_state_corruption": True,
        "require_validation_reference": False,
        "max_backtest_to_paper_return_degradation_pct": 50,
        "max_validation_to_paper_return_degradation_pct": 50,
        "require_human_approval_for_live": True,
    }
    data.update(overrides)
    return ReadinessSettings(**data)


def make_paper_run(tmp_path: Path, *, trades: bool = True) -> Path:
    store = PaperStateStore(tmp_path / "paper")
    state = new_paper_state(
        exchange="kraken",
        symbol="BTC/USDT",
        timeframe="4h",
        strategy="noop",
        starting_equity=1000,
        paper_run_id="paper-1",
    )
    state.created_at = datetime.now(UTC) - timedelta(days=2)
    state.updated_at = datetime.now(UTC)
    state.equity = 1010
    state.equity_curve = [
        {"timestamp": state.created_at, "equity": 1000, "position_quantity": 0},
        {"timestamp": state.updated_at, "equity": 1010, "position_quantity": 0},
    ]
    if trades:
        state.trades = [
            {
                "pnl": 10,
                "fees": 1,
                "entry_timestamp": state.created_at,
                "exit_timestamp": state.updated_at,
            }
        ]
    store.save(
        state,
        {
            "paper_run_id": "paper-1",
            "live_trading": False,
            "real_orders_enabled": False,
            "uses_private_api": False,
        },
    )
    return store.run_dir("paper-1")


def test_report_handles_zero_trades_without_crashing(tmp_path: Path) -> None:
    paper_dir = make_paper_run(tmp_path, trades=False)

    output = generate_paper_report(
        paper_run_dir=paper_dir,
        output_root=tmp_path / "reports",
        config_snapshot={"mode": "paper"},
        readiness_settings=readiness(),
    )

    metrics = json.loads((output / "paper_metrics.json").read_text(encoding="utf-8"))
    assert metrics["number_of_trades"] == 0


def test_report_handles_missing_alerts_file(tmp_path: Path) -> None:
    paper_dir = make_paper_run(tmp_path)
    (paper_dir / "alerts.jsonl").unlink(missing_ok=True)

    health = summarize_health(paper_dir=paper_dir, state=None, state_corruption=False)

    assert health["total_alerts"] == 0


def test_report_handles_corrupted_state_file_and_marks_corruption(tmp_path: Path) -> None:
    paper_dir = make_paper_run(tmp_path)
    (paper_dir / "state.json").write_text("{not json", encoding="utf-8")

    output = generate_paper_report(
        paper_run_dir=paper_dir,
        output_root=tmp_path / "reports",
        config_snapshot={"mode": "paper"},
        readiness_settings=readiness(),
    )

    health = json.loads((output / "health_summary.json").read_text(encoding="utf-8"))
    assert health["state_corruption_detected"] is True


def test_markdown_report_contains_required_limitations_text(tmp_path: Path) -> None:
    output = generate_paper_report(
        paper_run_dir=make_paper_run(tmp_path),
        output_root=tmp_path / "reports",
        config_snapshot={"mode": "paper"},
        readiness_settings=readiness(),
    )

    assert LIMITATIONS in (output / "report.md").read_text(encoding="utf-8")


def test_html_report_contains_readiness_status(tmp_path: Path) -> None:
    output = generate_paper_report(
        paper_run_dir=make_paper_run(tmp_path),
        output_root=tmp_path / "reports",
        config_snapshot={"mode": "paper"},
        readiness_settings=readiness(),
    )

    assert "ELIGIBLE_FOR_HUMAN_REVIEW" in (output / "report.html").read_text(encoding="utf-8")


def test_metadata_includes_safety_flags(tmp_path: Path) -> None:
    output = generate_paper_report(
        paper_run_dir=make_paper_run(tmp_path),
        output_root=tmp_path / "reports",
        config_snapshot={"mode": "paper"},
        readiness_settings=readiness(),
    )

    metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["live_trading"] is False
    assert metadata["real_orders_enabled"] is False
    assert metadata["uses_private_api"] is False
    assert metadata["human_approval_required_for_live"] is True

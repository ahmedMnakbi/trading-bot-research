from __future__ import annotations

import json
from pathlib import Path

from scripts import collect_strategy_tester_evidence, parse_strategy_tester_report

ROOT = Path(__file__).resolve().parents[1]


def _tester_report(
    *,
    trades: int = 0,
    orders: int = 0,
    deals: int = 0,
    settings: str = "EnableTrading=false\nEnablePropChallengeMode=false\n",
) -> str:
    return "\n".join(
        [
            "<html><body>",
            "Strategy Tester Report",
            "Symbol: EURUSD",
            "Timeframe: M5",
            "Model: Every tick based on real ticks",
            "Test period: 2026.05.01 - 2026.05.31",
            settings,
            f"Total trades: {trades}",
            f"Orders: {orders}",
            f"Deals: {deals}",
            "2026.06.01 12:00:00.000 UpcomersNYSessionPropBot monitor-only startup",
            "2026.06.01 12:01:00.000 UpcomersNYSessionPropBot Strategy signal=WAIT",
            "</body></html>",
        ]
    )


def _write_common_inputs(tmp_path: Path) -> dict[str, Path]:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    report_dir = inputs / "tester"
    report_dir.mkdir()
    (report_dir / "report.html").write_text(_tester_report(), encoding="utf-8")
    (report_dir / "terminal_password.log").write_text("password=hidden\n", encoding="utf-8")
    source_scan = inputs / "source_scan.json"
    source_scan.write_text(json.dumps({"status": "PASS", "violations": []}), encoding="utf-8")
    compile_log = inputs / "compile.log"
    compile_log.write_text("MetaEditor returned 0\n", encoding="utf-8")
    settings = inputs / "trial.set"
    settings.write_text(
        "\n".join(
            [
                "EnableTrading=false",
                "EnablePropChallengeMode=false",
                "AccountProgram=ACCOUNT_PROGRAM_TRIAL_RISK_FREE",
                "AccountStage=ACCOUNT_STAGE_TRIAL",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "report_dir": report_dir,
        "source_scan": source_scan,
        "compile_log": compile_log,
        "settings": settings,
    }


def test_strategy_tester_parser_handles_missing_files_with_warn(tmp_path: Path) -> None:
    result = parse_strategy_tester_report.parse_strategy_tester_report(
        tmp_path / "missing.html"
    )

    assert result.status == "WARN"
    assert "tester_report_missing" in result.warnings


def test_strategy_tester_parser_detects_zero_trades_as_pass(tmp_path: Path) -> None:
    report = tmp_path / "report.html"
    report.write_text(_tester_report(), encoding="utf-8")

    result = parse_strategy_tester_report.parse_strategy_tester_report(report)

    assert result.status == "PASS"
    assert result.symbol == "EURUSD"
    assert result.timeframe == "M5"
    assert result.modeling_mode == "Every tick based on real ticks"
    assert result.activity_counts == {"trades": 0, "orders": 0, "deals": 0}


def test_strategy_tester_parser_flags_trades_orders_or_deals_for_monitor_only(
    tmp_path: Path,
) -> None:
    report = tmp_path / "report.html"
    report.write_text(_tester_report(trades=1, orders=1, deals=1), encoding="utf-8")

    result = parse_strategy_tester_report.parse_strategy_tester_report(report)

    assert result.status == "FAIL"
    assert result.activity_counts["trades"] == 1
    assert "trade/order/deal activity" in result.message


def test_strategy_tester_parser_flags_unsafe_inputs(tmp_path: Path) -> None:
    report = tmp_path / "report.html"
    report.write_text(
        _tester_report(settings="EnableTrading=true\nEnablePropChallengeMode=false\n"),
        encoding="utf-8",
    )

    result = parse_strategy_tester_report.parse_strategy_tester_report(report)

    assert result.status == "FAIL"
    assert "enable_trading_unsafe" in result.warnings


def test_strategy_tester_collector_excludes_secret_like_files(tmp_path: Path) -> None:
    paths = _write_common_inputs(tmp_path)
    result = collect_strategy_tester_evidence.collect_strategy_tester_evidence(
        output_root=tmp_path / "out",
        run_id="tester-pass",
        tester_artifacts=[paths["report_dir"]],
        settings_file=paths["settings"],
        compile_log=paths["compile_log"],
        source_scan=paths["source_scan"],
    )

    package = Path(result.package_dir)
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))

    assert result.status == "WARN"  # secret-like file skip is recorded.
    assert manifest["evidence_kind"] == "monitor_only_tester_evidence"
    assert manifest["formal_trial_evidence"] is False
    assert manifest["trial_evidence_skipped"] is True
    assert (package / "tester_artifacts" / "report.html").exists()
    assert not (package / "tester_artifacts" / "terminal_password.log").exists()


def test_strategy_tester_docs_require_monitor_only_and_no_approval() -> None:
    text = (ROOT / "docs" / "strategy_tester_workflow.md").read_text(encoding="utf-8")

    assert "EnableTrading=false" in text
    assert "EnablePropChallengeMode=false" in text
    assert "EURUSD" in text
    assert "M5" in text
    assert "Every tick based on real ticks" in text
    assert "not a profitability claim" in text
    assert "does not approve" in text
    assert "Surge 2 Step" in text
    assert "Vanguard" in text


def test_order_calls_are_isolated_to_execution_modules() -> None:
    trial_execution = (
        ROOT / "mql5" / "Include" / "UpcomersNYSessionPropBot" / "TrialExecution.mqh"
    )
    tester_execution = (
        ROOT / "mql5" / "Include" / "UpcomersNYSessionPropBot" / "TesterExecution.mqh"
    )
    assert "OrderSend(request, result)" in trial_execution.read_text(encoding="utf-8")
    assert "OrderSend(request, result)" in tester_execution.read_text(encoding="utf-8")
    for path in (ROOT / "mql5").rglob("*"):
        if path.suffix.lower() not in {".mq5", ".mqh"} or path in {
            trial_execution,
            tester_execution,
        }:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in [
            "OrderSend",
            "CTrade",
            ".Buy(",
            ".Sell(",
            "PositionOpen",
            "BuyLimit",
            "SellLimit",
            "BuyStop",
            "SellStop",
        ]:
            assert pattern not in text

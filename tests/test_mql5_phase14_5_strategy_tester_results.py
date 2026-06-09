from __future__ import annotations

import json
from pathlib import Path

from scripts.collect_strategy_tester_evidence import collect_strategy_tester_evidence
from scripts.compare_strategy_tester_runs import compare_strategy_tester_runs
from scripts.parse_strategy_tester_report import parse_strategy_tester_report

ROOT = Path(__file__).resolve().parents[1]


def _simulated_report(
    *,
    strategy: str = "STRATEGY_VWAP_TREND_CONTINUATION",
    trades: int = 40,
    deals: int = 80,
    initial_balance: str = "10000.00",
    final_balance: str = "9992.08",
    net_profit: str = "-7.92",
    profit_factor: str = "0.82",
    drawdown: str = "12.50 (0.13%)",
) -> str:
    return "\n".join(
        [
            "Strategy Tester Report",
            "Symbol: EURUSD",
            "Timeframe: M5",
            "Modeling mode: Every tick based on real ticks",
            "Test period: 2026.04.01 - 2026.06.01",
            "Initial deposit: " + initial_balance,
            "Final balance: " + final_balance,
            "Net Profit: " + net_profit,
            "Profit Factor: " + profit_factor,
            "Maximal drawdown: " + drawdown,
            "Total trades: " + str(trades),
            "Orders: " + str(trades),
            "Deals: " + str(deals),
            "StrategyTesterExecutionMode=true",
            "EnableTrading=false",
            "EnableTrialExecution=false",
            "EnablePropChallengeMode=false",
            "StrategySelection=" + strategy,
            (
                "2026.06.01 12:00:00.000 STRATEGY_DIAGNOSTICS_SUMMARY "
                f"strategy={strategy} total_evaluations=12269 enter_long=21 "
                "enter_short=19 tester_execution_mode=true tester_runtime=true "
                "tester_orders_attempted=40 top_reason_codes=WAIT:111|ENTER_LONG_INTENT:21"
            ),
            (
                "2026.06.01 12:00:01.000 TESTER_EXECUTION_SUMMARY "
                "tester_entry_intents_received=40 tester_orders_attempted=40 "
                "tester_orders_sent_success=40 tester_orders_rejected=0 "
                "tester_orders_skipped_by_gate=0"
            ),
        ]
    )


def test_strategy_tester_parser_extracts_phase14_5_performance_fields(
    tmp_path: Path,
) -> None:
    report = tmp_path / "vwap_report.html"
    report.write_text(_simulated_report(), encoding="utf-8")

    result = parse_strategy_tester_report(report, monitor_only=False)

    assert result.status == "PASS"
    assert result.activity_counts["trades"] == 40
    assert result.activity_counts["deals"] == 80
    assert result.performance_metrics["initial_balance"] == 10000.0
    assert result.performance_metrics["final_balance"] == 9992.08
    assert result.performance_metrics["net_profit"] == -7.92
    assert result.performance_metrics["return_percent"] == -0.0792
    assert result.performance_metrics["profit_factor"] == "0.82"
    assert result.performance_metrics["max_drawdown"] == "12.50 (0.13%)"
    assert result.strategy_diagnostics["enter_long"] == 21
    assert result.tester_execution_summary["tester_orders_sent_success"] == 40


def test_strategy_tester_collector_accepts_artifact_folder_with_settings_and_summary(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "tester_export"
    input_dir.mkdir()
    (input_dir / "report.html").write_text(_simulated_report(), encoding="utf-8")
    (input_dir / "tester.log").write_text(
        "TESTER_EXECUTION_SUMMARY tester_entry_intents_received=40 "
        "tester_orders_attempted=40 tester_orders_sent_success=40 "
        "tester_orders_rejected=0\n",
        encoding="utf-8",
    )
    (input_dir / "strategy_tester_eurusd_m5_vwap.set").write_text(
        "\n".join(
            [
                "StrategyTesterExecutionMode=true",
                "EnableTrading=false",
                "EnableTrialExecution=false",
                "StrategySelection=STRATEGY_VWAP_TREND_CONTINUATION",
            ]
        ),
        encoding="utf-8",
    )
    (input_dir / "strategy_tester_eurusd_m5_vwap.summary.json").write_text(
        json.dumps({"preset_name": "strategy-tester-eurusd-m5-vwap"}),
        encoding="utf-8",
    )
    (input_dir / "account_token.txt").write_text("token=secret", encoding="utf-8")

    result = collect_strategy_tester_evidence(
        output_root=tmp_path / "out",
        run_id="phase14_5_vwap",
        tester_artifacts=[input_dir],
        simulated_execution=True,
    )

    package_dir = Path(result.package_dir)
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    parser_summary = json.loads(
        (package_dir / "parser_summary.json").read_text(encoding="utf-8")
    )

    assert result.status == "WARN"  # secret-like file skip is recorded.
    assert manifest["evidence_kind"] == "strategy_tester_simulated_execution_research_evidence"
    assert manifest["simulated_execution"] is True
    assert parser_summary["status"] == "PASS"
    assert parser_summary["performance_metrics"]["net_profit"] == -7.92
    assert (package_dir / "settings" / "strategy_tester_eurusd_m5_vwap.set").exists()
    assert (
        package_dir
        / "settings_summary"
        / "strategy_tester_eurusd_m5_vwap.summary.json"
    ).exists()
    assert not (package_dir / "tester_artifacts" / "account_token.txt").exists()


def test_strategy_tester_comparator_writes_json_and_markdown(tmp_path: Path) -> None:
    vwap_summary = parse_strategy_tester_report(
        _write_report(tmp_path, "vwap.html", _simulated_report()),
        monitor_only=False,
    )
    orb_summary = parse_strategy_tester_report(
        _write_report(
            tmp_path,
            "orb.html",
            _simulated_report(
                strategy="STRATEGY_OPENING_RANGE_BREAKOUT",
                trades=42,
                deals=84,
                final_balance="9996.37",
                net_profit="-3.63",
                profit_factor="0.91",
            ),
        ),
        monitor_only=False,
    )
    vwap_path = tmp_path / "vwap_parser_summary.json"
    orb_path = tmp_path / "orb_parser_summary.json"
    vwap_path.write_text(json.dumps(vwap_summary.to_dict()), encoding="utf-8")
    orb_path.write_text(json.dumps(orb_summary.to_dict()), encoding="utf-8")

    result = compare_strategy_tester_runs(
        [vwap_path, orb_path],
        output_json=tmp_path / "comparison.json",
        output_md=tmp_path / "comparison.md",
    )

    comparison_json = json.loads((tmp_path / "comparison.json").read_text(encoding="utf-8"))
    comparison_md = (tmp_path / "comparison.md").read_text(encoding="utf-8")

    assert result.status == "PASS"
    assert len(result.rows) == 2
    assert comparison_json["research_only"] is True
    assert comparison_json["trading_approval"] is False
    assert "STRATEGY_VWAP_TREND_CONTINUATION" in comparison_md
    assert "STRATEGY_OPENING_RANGE_BREAKOUT" in comparison_md
    assert "net_profit" in comparison_md
    assert "-7.92" in comparison_md
    assert "-3.63" in comparison_md


def test_strategy_tester_docs_explain_export_collect_compare_and_research_only() -> None:
    text = (ROOT / "docs" / "strategy_tester_workflow.md").read_text(encoding="utf-8")

    assert "exported Strategy Tester HTML/XML/CSV report" in text
    assert "collect_strategy_tester_evidence.py" in text
    assert "compare_strategy_tester_runs.py" in text
    assert "ORB vs VWAP" in text
    assert "research-only" in text
    assert "does not approve" in text


def _write_report(tmp_path: Path, name: str, text: str) -> Path:
    report = tmp_path / name
    report.write_text(text, encoding="utf-8")
    return report

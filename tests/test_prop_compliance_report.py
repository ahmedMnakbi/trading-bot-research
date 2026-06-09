from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import export_prop_compliance_report
from trading_bot.mql5.compliance_report import export_prop_compliance_report as export_report
from trading_bot.mql5.log_parser import parse_ea_logs
from trading_bot.mql5.settings import generate_settings_artifacts
from trading_bot.mql5.source_scan import scan_mql5_source_tree
from trading_bot.mt5.safety import find_mt5_prohibited_patterns


def test_compliance_report_includes_upcomers_limits_and_blockers(tmp_path: Path) -> None:
    source_scan_path = tmp_path / "source_scan.json"
    source_scan_path.write_text(
        json.dumps(scan_mql5_source_tree(Path(__file__).resolve().parents[1]).to_dict()),
        encoding="utf-8",
    )
    settings = generate_settings_artifacts(output_path=tmp_path / "trial.set")
    logs = parse_ea_logs(tmp_path / "missing_logs", output_dir=tmp_path / "logs")
    compile_log = tmp_path / "compile.log"
    compile_log.write_text("MetaEditor returned 0\n", encoding="utf-8")

    result = export_report(
        output_dir=tmp_path / "reports",
        source_scan_path=source_scan_path,
        compile_log_path=compile_log,
        settings_summary_path=settings.summary_json_path,
        log_summary_path=logs.summary_json_path,
    )

    report = json.loads(Path(result.report_json_path).read_text(encoding="utf-8"))
    markdown = Path(result.report_md_path).read_text(encoding="utf-8")
    assert report["upcomers_rule_mapping"]["daily_loss_limit"]["prop_limit"] == "4%"
    assert report["upcomers_rule_mapping"]["overall_loss_limit"]["prop_limit"] == "7%"
    assert "daily reset timezone confirmation" in report["blockers"]
    assert "Dynamic Risk Shield exact calculation" in report["blockers"]
    assert "Surge 2 Step exact rules review and encoding" in report["blockers"]
    assert report["build_evidence_complete"] is True
    assert report["monitor_evidence_complete"] is False
    assert report["trial_evidence_complete"] is False
    assert report["strategy_tester_evidence_complete"] is False
    assert result.evidence_complete is False
    assert "Python is not the execution layer" in markdown


def test_compliance_report_states_protected_programs_remain_blocked(tmp_path: Path) -> None:
    result = export_report(output_dir=tmp_path / "reports")

    report = json.loads(Path(result.report_json_path).read_text(encoding="utf-8"))
    markdown = Path(result.report_md_path).read_text(encoding="utf-8")
    assert report["safety_statements"]["vanguard_blocked"] is True
    assert report["safety_statements"]["surge_2_step_rule_unverified"] is True
    assert report["safety_statements"]["account_program_awareness"] == [
        "TrialRiskFree",
        "Vanguard",
        "Surge2Step",
        "Custom",
    ]
    assert "Surge 2 Step is rule-unverified" in markdown
    assert "Vanguard remains blocked" in markdown
    assert result.evidence_complete is False


def test_compliance_report_marks_all_evidence_complete_when_all_sections_exist(
    tmp_path: Path,
) -> None:
    source_scan_path = tmp_path / "source_scan.json"
    source_scan_path.write_text('{"status": "PASS"}', encoding="utf-8")
    settings_path = tmp_path / "settings.json"
    settings_path.write_text('{"status": "PASS"}', encoding="utf-8")
    compile_log = tmp_path / "compile.log"
    compile_log.write_text("MetaEditor returned 0\n", encoding="utf-8")
    monitor_log_summary = tmp_path / "ea_logs.json"
    monitor_log_summary.write_text(
        '{"status": "PASS", "files_scanned": 1}',
        encoding="utf-8",
    )
    trial_evidence = tmp_path / "trial_evidence.json"
    trial_evidence.write_text('{"trial": "observed"}', encoding="utf-8")
    tester_evidence = tmp_path / "tester"
    tester_evidence.mkdir()
    (tester_evidence / "report.htm").write_text("tester report", encoding="utf-8")

    result = export_report(
        output_dir=tmp_path / "reports",
        source_scan_path=source_scan_path,
        compile_log_path=compile_log,
        settings_summary_path=settings_path,
        log_summary_path=monitor_log_summary,
        trial_evidence_path=trial_evidence,
        strategy_tester_evidence_path=tester_evidence,
    )

    report = json.loads(Path(result.report_json_path).read_text(encoding="utf-8"))
    assert report["build_evidence_complete"] is True
    assert report["monitor_evidence_complete"] is True
    assert report["trial_evidence_complete"] is True
    assert report["strategy_tester_evidence_complete"] is True
    assert result.evidence_complete is True


def test_compliance_report_states_python_support_only(tmp_path: Path) -> None:
    result = export_report(output_dir=tmp_path / "reports")
    report = json.loads(Path(result.report_json_path).read_text(encoding="utf-8"))

    assert report["safety_statements"]["python_is_execution_layer"] is False
    assert "support-only" in report["safety_statements"]["python_role"]


def test_no_python_mt5_prop_execution_path_is_enabled() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "trading_bot"

    assert find_mt5_prohibited_patterns(root) == []


def test_export_prop_compliance_report_script_help_works(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        export_prop_compliance_report.main(["--help"])

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "Export a prop-firm" in output
    assert "--trial-evidence-path" in output

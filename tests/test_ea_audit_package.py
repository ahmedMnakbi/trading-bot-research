from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import export_ea_audit_package as export_script
from trading_bot.mql5.audit_package import export_ea_audit_package


def _write_minimal_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    source_dir = project / "mql5" / "Experts" / "UpcomersNYSessionPropBot"
    include_dir = project / "mql5" / "Include" / "UpcomersNYSessionPropBot"
    docs_dir = project / "docs"
    source_dir.mkdir(parents=True)
    include_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)
    (source_dir / "UpcomersNYSessionPropBot.mq5").write_text(
        "\n".join(
            [
                "input bool EnableTrading = false;",
                "input bool EnablePropChallengeMode = false;",
                "void OnTick() { return; }",
            ]
        ),
        encoding="utf-8",
    )
    (include_dir / "TradeManager.mqh").write_text(
        "bool RefuseExecution() { return false; }\n",
        encoding="utf-8",
    )
    (project / "README.md").write_text("Native MQL5 EA path\n", encoding="utf-8")
    (project / "SAFETY.md").write_text("Trading disabled by default\n", encoding="utf-8")
    (project / "AGENTS.md").write_text("Python support-only\n", encoding="utf-8")
    (docs_dir / "setup.md").write_text(
        "api_key=super-secret-value\nNo credentials belong here.\n",
        encoding="utf-8",
    )
    (project / ".env").write_text("PASSWORD=do-not-copy\n", encoding="utf-8")
    return project


def _write_evidence(project: Path) -> dict[str, Path]:
    evidence_dir = project / "inputs"
    evidence_dir.mkdir()
    source_scan = evidence_dir / "source_scan.json"
    source_scan.write_text(
        json.dumps({"status": "PASS", "violations": [], "safeguards": []}),
        encoding="utf-8",
    )
    compile_log = evidence_dir / "compile.log"
    compile_log.write_text("MetaEditor returned 0\n", encoding="utf-8")
    settings = evidence_dir / "trial.summary.json"
    settings.write_text(
        json.dumps(
            {
                "status": "PASS",
                "monitor_only": True,
                "account_program": "TrialRiskFree",
                "account_stage": "Trial",
                "trading_enabled": False,
                "prop_challenge_mode": False,
                "settings": {
                    "account_program": "TrialRiskFree",
                    "account_stage": "Trial",
                    "enable_trading": False,
                    "enable_prop_challenge_mode": False,
                },
            }
        ),
        encoding="utf-8",
    )
    compliance = evidence_dir / "prop_compliance.json"
    compliance.write_text(
        json.dumps(
            {
                "status": "WARN",
                "upcomers_rule_mapping": {
                    "daily_loss_limit": {"prop_limit": "4%", "ea_hard_limit": "3%"},
                    "overall_loss_limit": {"prop_limit": "7%", "ea_hard_limit": "6%"},
                },
                "safety_statements": {
                    "surge_2_step_rule_unverified": True,
                    "vanguard_blocked": True,
                    "python_is_execution_layer": False,
                },
            }
        ),
        encoding="utf-8",
    )
    return {
        "source_scan": source_scan,
        "compile_log": compile_log,
        "settings": settings,
        "compliance": compliance,
    }


def test_ea_audit_package_writes_required_files_and_snapshots(tmp_path: Path) -> None:
    project = _write_minimal_project(tmp_path)
    evidence = _write_evidence(project)

    result = export_ea_audit_package(
        output_dir=tmp_path / "packages",
        source_scan_path=evidence["source_scan"],
        compile_log_path=evidence["compile_log"],
        settings_summary_path=evidence["settings"],
        prop_compliance_report_path=evidence["compliance"],
        project_root=project,
        package_id="package-test",
    )

    package_dir = Path(result.package_dir)
    for required in [
        "package_manifest.json",
        "audit_summary.json",
        "source_hashes.json",
        "mql5_source_scan.json",
        "compile_summary.json",
        "settings_summary.json",
        "prop_compliance_summary.json",
        "evidence_status.json",
        "known_blockers.json",
        "README.md",
    ]:
        assert (package_dir / required).exists()
    assert (package_dir / "docs_snapshot").is_dir()
    assert (package_dir / "mql5_source_snapshot").is_dir()
    assert (package_dir / "reports").is_dir()


def test_ea_audit_package_evidence_and_blocker_semantics(tmp_path: Path) -> None:
    project = _write_minimal_project(tmp_path)
    evidence = _write_evidence(project)

    result = export_ea_audit_package(
        output_dir=tmp_path / "packages",
        source_scan_path=evidence["source_scan"],
        compile_log_path=evidence["compile_log"],
        settings_summary_path=evidence["settings"],
        prop_compliance_report_path=evidence["compliance"],
        project_root=project,
        package_id="package-test",
    )

    package_dir = Path(result.package_dir)
    evidence_status = json.loads((package_dir / "evidence_status.json").read_text())
    blockers = json.loads((package_dir / "known_blockers.json").read_text())
    summary = json.loads((package_dir / "audit_summary.json").read_text())

    assert evidence_status["source_evidence"]["mql5_source_present"] is True
    assert evidence_status["source_evidence"]["source_scan_pass"] is True
    assert evidence_status["source_evidence"]["no_order_placement_calls"] is True
    assert evidence_status["compile_evidence"]["compile_pass"] is True
    assert evidence_status["settings_evidence"]["trial_monitor_only_set_generated"] is True
    assert evidence_status["settings_evidence"]["trading_disabled"] is True
    assert evidence_status["settings_evidence"]["prop_challenge_mode_disabled"] is True
    assert evidence_status["compliance_evidence"]["prop_compliance_report_generated"] is True
    assert evidence_status["compliance_evidence"]["surge_exact_rules_unverified"] is True
    assert evidence_status["compliance_evidence"]["vanguard_exact_rules_unverified"] is True
    assert evidence_status["missing_evidence"]["real_monitor_only_ea_logs_missing"] is True
    assert evidence_status["missing_evidence"]["trial_observation_evidence_missing"] is True
    assert evidence_status["missing_evidence"]["strategy_tester_evidence_missing"] is True
    assert any("Surge 2 Step exact rule review" in item for item in blockers["blockers"])
    assert any("Vanguard exact rule review" in item for item in blockers["blockers"])
    assert summary["trial_approved_for_trading"] is False
    assert summary["surge_approved_for_trading"] is False
    assert summary["vanguard_approved_for_trading"] is False
    assert summary["python_prop_execution_allowed"] is False
    assert summary["native_mql5_ea_execution_path"] is True
    assert summary["trading_enabled_by_default"] is False


def test_ea_audit_package_hashes_sources_and_redacts_secrets(tmp_path: Path) -> None:
    project = _write_minimal_project(tmp_path)
    evidence = _write_evidence(project)

    result = export_ea_audit_package(
        output_dir=tmp_path / "packages",
        source_scan_path=evidence["source_scan"],
        compile_log_path=evidence["compile_log"],
        settings_summary_path=evidence["settings"],
        prop_compliance_report_path=evidence["compliance"],
        project_root=project,
        package_id="package-test",
    )

    package_dir = Path(result.package_dir)
    hashes = json.loads((package_dir / "source_hashes.json").read_text())
    snapshot_text = (package_dir / "docs_snapshot" / "docs" / "setup.md").read_text()

    assert hashes["file_count"] >= 2
    assert all(entry["sha256"] for entry in hashes["files"])
    assert not list(package_dir.rglob(".env"))
    assert "super-secret-value" not in snapshot_text
    assert "api_key=<REDACTED>" in snapshot_text


def test_ea_audit_package_does_not_claim_live_approval(tmp_path: Path) -> None:
    project = _write_minimal_project(tmp_path)
    evidence = _write_evidence(project)

    result = export_ea_audit_package(
        output_dir=tmp_path / "packages",
        source_scan_path=evidence["source_scan"],
        compile_log_path=evidence["compile_log"],
        settings_summary_path=evidence["settings"],
        prop_compliance_report_path=evidence["compliance"],
        project_root=project,
        package_id="package-test",
    )

    readme = Path(result.package_dir, "README.md").read_text(encoding="utf-8")
    assert "Trial Risk-Free trading: blocked" in readme
    assert "Surge 2 Step trading: blocked" in readme
    assert "Vanguard trading: blocked" in readme
    assert "ready for live" not in readme.lower()
    assert "proven profitable" not in readme.lower()


def test_ea_audit_package_handles_missing_optional_inputs(tmp_path: Path) -> None:
    project = _write_minimal_project(tmp_path)

    result = export_ea_audit_package(
        output_dir=tmp_path / "packages",
        project_root=project,
        package_id="missing-inputs",
    )

    evidence_status = json.loads(Path(result.evidence_status_path).read_text())
    assert result.status == "INCOMPLETE_FOR_SOURCE_REVIEW"
    assert evidence_status["compile_evidence"]["compile_pass"] is False
    assert evidence_status["settings_evidence"]["complete"] is False
    assert evidence_status["compliance_evidence"]["complete"] is False
    assert evidence_status["missing_evidence"]["real_monitor_only_ea_logs_missing"] is True


def test_export_ea_audit_package_script_help_works(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        export_script.main(["--help"])

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "Export a local native MQL5 EA audit package" in output
    assert "--source-scan-path" in output

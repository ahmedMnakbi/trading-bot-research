from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import collect_trial_observation_evidence, verify_trial_observation_package


def _write_required_inputs(tmp_path: Path) -> dict[str, Path]:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    logs = inputs / "logs"
    logs.mkdir()
    (logs / "monitor.log").write_text(
        "\n".join(
            [
                "2026.06.01 12:00:00.000\tUpcomersNYSessionPropBot "
                "(EURUSD,M5)\tMonitor-only startup",
                "2026.06.01 12:01:00.000\tUpcomersNYSessionPropBot "
                "(EURUSD,M5)\tStrategy signal=WAIT no order placement",
            ]
        ),
        encoding="utf-8",
    )
    (logs / "account_passwords.log").write_text("password=do-not-copy\n", encoding="utf-8")
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
    broker_note = inputs / "broker_time.md"
    broker_note.write_text("BrokerServerUtcOffsetMinutes verified manually.\n", encoding="utf-8")
    symbol_checklist = inputs / "symbol_session.md"
    symbol_checklist.write_text("Symbol sessions and spread observed manually.\n", encoding="utf-8")
    no_trades = inputs / "no_trial_trades.md"
    no_trades.write_text(
        "Orders opened: 0\nPositions opened: 0\nNo orders and no positions occurred.\n",
        encoding="utf-8",
    )
    project = tmp_path / "project"
    mql5 = project / "mql5" / "Experts"
    support = project / "src" / "trading_bot" / "mql5"
    mql5.mkdir(parents=True)
    support.mkdir(parents=True)
    (mql5 / "Safe.mq5").write_text("void OnTick() {}\n", encoding="utf-8")
    return {
        "logs": logs,
        "source_scan": source_scan,
        "compile_log": compile_log,
        "settings": settings,
        "broker_note": broker_note,
        "symbol_checklist": symbol_checklist,
        "no_trades": no_trades,
        "project": project,
    }


def test_collect_trial_observation_evidence_help_works(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        collect_trial_observation_evidence.main(["--help"])

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "Trial monitor-only" in output
    assert "credential" not in output.lower()
    assert "password" not in output.lower()


def test_verify_trial_observation_package_help_works(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        verify_trial_observation_package.main(["--help"])

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "Trial monitor-only" in output
    assert "credential" not in output.lower()


def test_collector_redacts_secret_like_values_and_excludes_secret_files(tmp_path: Path) -> None:
    paths = _write_required_inputs(tmp_path)
    paths["broker_note"].write_text(
        "BrokerServerUtcOffsetMinutes verified manually.\ntoken=do-not-copy\n",
        encoding="utf-8",
    )
    result = collect_trial_observation_evidence.collect_trial_observation_evidence(
        output_root=tmp_path / "out",
        project_root=paths["project"],
        run_id="trial-test",
        ea_logs=paths["logs"],
        settings_file=paths["settings"],
        compile_log=paths["compile_log"],
        source_scan=paths["source_scan"],
        broker_time_note=paths["broker_note"],
        symbol_session_checklist=paths["symbol_checklist"],
        no_trial_trades_note=paths["no_trades"],
    )

    package = Path(result.package_dir)
    copied_log = package / "ea_monitor_logs" / "monitor.log"
    excluded_log = package / "ea_monitor_logs" / "account_passwords.log"
    copied_broker_note = package / "broker_time_verification" / "broker_time.md"
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))

    assert result.status == "WARN"  # secret-like file skip is recorded.
    assert copied_log.exists()
    assert copied_log.read_text(encoding="utf-8") == (
        paths["logs"] / "monitor.log"
    ).read_text(encoding="utf-8")
    assert "token=<REDACTED>" in copied_broker_note.read_text(encoding="utf-8")
    assert not excluded_log.exists()
    assert manifest["credentials_collected"] is False


def test_verifier_passes_complete_monitor_only_package_without_screenshots(
    tmp_path: Path,
) -> None:
    paths = _write_required_inputs(tmp_path)
    result = collect_trial_observation_evidence.collect_trial_observation_evidence(
        output_root=tmp_path / "out",
        project_root=paths["project"],
        run_id="trial-complete",
        ea_logs=paths["logs"],
        settings_file=paths["settings"],
        compile_log=paths["compile_log"],
        source_scan=paths["source_scan"],
        broker_time_note=paths["broker_note"],
        symbol_session_checklist=paths["symbol_checklist"],
        no_trial_trades_note=paths["no_trades"],
    )

    verification = verify_trial_observation_package.verify_trial_observation_package(
        result.package_dir
    )

    assert verification.status == "PASS"
    assert verification.evidence_kind == "formal_trial_observation"
    assert verification.failures == []
    assert verification.warnings == []


def test_missing_logs_produce_warn_not_pass(tmp_path: Path) -> None:
    paths = _write_required_inputs(tmp_path)
    result = collect_trial_observation_evidence.collect_trial_observation_evidence(
        output_root=tmp_path / "out",
        project_root=paths["project"],
        run_id="trial-missing-logs",
        evidence_kind="trial_monitor_smoke",
        settings_file=paths["settings"],
        compile_log=paths["compile_log"],
        source_scan=paths["source_scan"],
        broker_time_note=paths["broker_note"],
        symbol_session_checklist=paths["symbol_checklist"],
        no_trial_trades_note=paths["no_trades"],
    )

    verification = verify_trial_observation_package.verify_trial_observation_package(
        result.package_dir
    )

    assert verification.status == "WARN"
    assert "ea_monitor_logs" in verification.warnings
    assert "ea_monitor_logs" not in verification.failures


def test_verification_requires_monitor_logs_for_trial_evidence_pass(tmp_path: Path) -> None:
    paths = _write_required_inputs(tmp_path)
    result = collect_trial_observation_evidence.collect_trial_observation_evidence(
        output_root=tmp_path / "out",
        project_root=paths["project"],
        run_id="trial-no-logs",
        settings_file=paths["settings"],
        compile_log=paths["compile_log"],
        source_scan=paths["source_scan"],
        broker_time_note=paths["broker_note"],
        symbol_session_checklist=paths["symbol_checklist"],
        no_trial_trades_note=paths["no_trades"],
    )

    verification = verify_trial_observation_package.verify_trial_observation_package(
        result.package_dir
    )

    checks = {check.name: check for check in verification.checks}
    assert checks["ea_monitor_logs"].status == "FAIL"
    assert verification.status != "PASS"
    assert "ea_monitor_logs" in verification.failures


def test_formal_evidence_requires_broker_time_note_for_pass(tmp_path: Path) -> None:
    paths = _write_required_inputs(tmp_path)
    result = collect_trial_observation_evidence.collect_trial_observation_evidence(
        output_root=tmp_path / "out",
        project_root=paths["project"],
        run_id="trial-no-broker-note",
        ea_logs=paths["logs"],
        settings_file=paths["settings"],
        compile_log=paths["compile_log"],
        source_scan=paths["source_scan"],
        symbol_session_checklist=paths["symbol_checklist"],
        no_trial_trades_note=paths["no_trades"],
    )

    verification = verify_trial_observation_package.verify_trial_observation_package(
        result.package_dir
    )

    assert verification.status == "FAIL"
    assert "broker_time_verification" in verification.failures


def test_formal_evidence_requires_symbol_session_note_for_pass(tmp_path: Path) -> None:
    paths = _write_required_inputs(tmp_path)
    result = collect_trial_observation_evidence.collect_trial_observation_evidence(
        output_root=tmp_path / "out",
        project_root=paths["project"],
        run_id="trial-no-symbol-note",
        ea_logs=paths["logs"],
        settings_file=paths["settings"],
        compile_log=paths["compile_log"],
        source_scan=paths["source_scan"],
        broker_time_note=paths["broker_note"],
        no_trial_trades_note=paths["no_trades"],
    )

    verification = verify_trial_observation_package.verify_trial_observation_package(
        result.package_dir
    )

    assert verification.status == "FAIL"
    assert "symbol_session_verification" in verification.failures


def test_formal_evidence_requires_no_order_no_position_note(tmp_path: Path) -> None:
    paths = _write_required_inputs(tmp_path)
    result = collect_trial_observation_evidence.collect_trial_observation_evidence(
        output_root=tmp_path / "out",
        project_root=paths["project"],
        run_id="trial-no-order-note",
        ea_logs=paths["logs"],
        settings_file=paths["settings"],
        compile_log=paths["compile_log"],
        source_scan=paths["source_scan"],
        broker_time_note=paths["broker_note"],
        symbol_session_checklist=paths["symbol_checklist"],
    )

    verification = verify_trial_observation_package.verify_trial_observation_package(
        result.package_dir
    )

    assert verification.status == "FAIL"
    assert "no_order_no_position" in verification.failures


def test_formal_evidence_rejects_cleaned_or_edited_log_excerpts(tmp_path: Path) -> None:
    paths = _write_required_inputs(tmp_path)
    cleaned_logs = paths["logs"]
    (cleaned_logs / "monitor.log").write_text(
        "CLEANED EXCERPT: monitor-only startup, no errors, no orders.\n",
        encoding="utf-8",
    )
    result = collect_trial_observation_evidence.collect_trial_observation_evidence(
        output_root=tmp_path / "out",
        project_root=paths["project"],
        run_id="trial-cleaned-logs",
        ea_logs=cleaned_logs,
        settings_file=paths["settings"],
        compile_log=paths["compile_log"],
        source_scan=paths["source_scan"],
        broker_time_note=paths["broker_note"],
        symbol_session_checklist=paths["symbol_checklist"],
        no_trial_trades_note=paths["no_trades"],
    )

    verification = verify_trial_observation_package.verify_trial_observation_package(
        result.package_dir
    )

    assert verification.status == "FAIL"
    assert "ea_monitor_logs" in verification.failures


def test_evidence_scripts_do_not_require_credentials() -> None:
    collect_help = collect_trial_observation_evidence.build_parser().format_help().lower()
    verify_help = verify_trial_observation_package.build_parser().format_help().lower()

    assert "password" not in collect_help
    assert "password" not in verify_help
    assert "credential" not in collect_help
    assert "credential" not in verify_help


def test_smoke_evidence_is_distinct_from_formal_trial_observation(tmp_path: Path) -> None:
    paths = _write_required_inputs(tmp_path)
    result = collect_trial_observation_evidence.collect_trial_observation_evidence(
        output_root=tmp_path / "out",
        project_root=paths["project"],
        run_id="trial-smoke",
        evidence_kind="trial_monitor_smoke",
        settings_file=paths["settings"],
        compile_log=paths["compile_log"],
        source_scan=paths["source_scan"],
        no_trial_trades_note=paths["no_trades"],
    )

    verification = verify_trial_observation_package.verify_trial_observation_package(
        result.package_dir
    )
    checks = {check.name: check for check in verification.checks}

    assert result.evidence_kind == "trial_monitor_smoke"
    assert verification.evidence_kind == "trial_monitor_smoke"
    assert verification.status == "WARN"
    assert checks["evidence_classification"].status == "WARN"
    assert checks["broker_time_verification"].status == "WARN"
    assert checks["symbol_session_verification"].status == "WARN"
    assert "smoke_evidence_only" in verification.warnings
    assert "broker_time_verification" not in verification.failures
    assert "symbol_session_verification" not in verification.failures


def test_strategy_tester_evidence_is_separate_from_trial_observation(tmp_path: Path) -> None:
    paths = _write_required_inputs(tmp_path)
    result = collect_trial_observation_evidence.collect_trial_observation_evidence(
        output_root=tmp_path / "out",
        project_root=paths["project"],
        run_id="strategy-tester",
        evidence_kind="strategy_tester",
        ea_logs=paths["logs"],
        settings_file=paths["settings"],
        compile_log=paths["compile_log"],
        source_scan=paths["source_scan"],
        broker_time_note=paths["broker_note"],
        symbol_session_checklist=paths["symbol_checklist"],
        no_trial_trades_note=paths["no_trades"],
    )

    verification = verify_trial_observation_package.verify_trial_observation_package(
        result.package_dir
    )

    assert verification.evidence_kind == "strategy_tester"
    assert verification.status == "WARN"
    assert "strategy_tester_evidence_not_trial_observation" in verification.warnings


def test_create_trial_observation_notes_writes_required_templates(tmp_path: Path) -> None:
    from scripts import create_trial_observation_notes

    result = create_trial_observation_notes.create_trial_observation_notes(
        run_id="trial-formal",
        output_root=tmp_path / "manual",
    )
    output = Path(result.output_dir)

    assert result.status == "PASS"
    assert (output / "broker_time_note.txt").exists()
    assert (output / "symbol_session_note.txt").exists()
    assert (output / "no_order_no_position_note.txt").exists()
    assert "Orders opened: 0" in (output / "no_order_no_position_note.txt").read_text(
        encoding="utf-8"
    )


def test_order_calls_are_isolated_to_execution_modules() -> None:
    root = Path(__file__).resolve().parents[1]
    trial_execution = (
        root / "mql5" / "Include" / "UpcomersNYSessionPropBot" / "TrialExecution.mqh"
    )
    tester_execution = (
        root / "mql5" / "Include" / "UpcomersNYSessionPropBot" / "TesterExecution.mqh"
    )
    assert "OrderSend(request, result)" in trial_execution.read_text(encoding="utf-8")
    assert "OrderSend(request, result)" in tester_execution.read_text(encoding="utf-8")
    for path in (root / "mql5").rglob("*"):
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
        ]:
            assert pattern not in text

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import generate_ea_settings
from trading_bot.mql5.models import ApprovalMetadata
from trading_bot.mql5.settings import (
    TRIAL_EXECUTION_MANUAL_CONFIRMATION,
    TRIAL_MICRO_EXECUTION_PRESET,
    EaSettingsError,
    build_settings,
    generate_settings_artifacts,
)


def test_settings_generator_defaults_to_trial_monitor_only_and_trading_disabled(
    tmp_path: Path,
) -> None:
    result = generate_settings_artifacts(output_path=tmp_path / "trial.set")

    text = Path(result.set_path).read_text(encoding="utf-8")
    summary = json.loads(Path(result.summary_json_path).read_text(encoding="utf-8"))
    assert "AccountProgram=ACCOUNT_PROGRAM_TRIAL_RISK_FREE" in text
    assert "AccountStage=ACCOUNT_STAGE_TRIAL" in text
    assert "EnableTrading=false" in text
    assert "EnableTrialExecution=false" in text
    assert "EnablePropChallengeMode=false" in text
    assert "MaxTradesPerDay=1" in text
    assert "AllowedSymbols=EURUSD" in text
    assert summary["monitor_only"] is True
    assert summary["trial_execution_enabled"] is False
    assert summary["account_program"] == "TrialRiskFree"
    assert summary["python_is_execution_layer"] is False


def test_settings_generator_rejects_unsafe_risk_limits() -> None:
    with pytest.raises(EaSettingsError, match="daily hard loss"):
        build_settings(overrides={"max_daily_loss_hard_pct": 4.0})

    with pytest.raises(EaSettingsError, match="max risk"):
        build_settings(overrides={"max_risk_per_trade_pct": 0.51})


def test_settings_generator_rejects_protected_stage_without_metadata() -> None:
    with pytest.raises(EaSettingsError, match="protected stage missing approval metadata"):
        build_settings(stage="Challenge")


def test_settings_generator_allows_protected_stage_with_required_metadata() -> None:
    settings = build_settings(
        stage="Challenge",
        approval_metadata=ApprovalMetadata(
            account_program_rules_review_id="rules-1",
            trial_evidence_id="trial-1",
            source_scan_pass_id="scan-1",
            compile_pass_id="compile-1",
            final_audit_package_id="audit-1",
            human_approval_id="human-1",
        ),
    )

    assert settings.account_stage == "Challenge"


def test_settings_generator_marks_surge_rule_unverified_and_blocks_challenge() -> None:
    settings = build_settings(account_program="Surge2Step", stage="MonitorOnly")
    assert settings.account_program == "Surge2Step"

    with pytest.raises(EaSettingsError, match="rules are unverified"):
        build_settings(account_program="Surge2Step", stage="Challenge")


def test_settings_generator_rejects_trading_without_strict_confirmation() -> None:
    with pytest.raises(EaSettingsError, match="strict manual confirmation"):
        build_settings(overrides={"enable_trading": True})


def test_settings_generator_emits_set_json_and_markdown(tmp_path: Path) -> None:
    output = tmp_path / "safe.set"
    result = generate_settings_artifacts(output_path=output)

    assert output.exists()
    assert Path(result.summary_json_path).exists()
    assert Path(result.summary_md_path).exists()
    summary_md = Path(result.summary_md_path).read_text(encoding="utf-8")
    assert "Protected account programs blocked: true" in summary_md
    assert "Surge 2 Step rule-unverified: true" in summary_md


def test_generate_ea_settings_script_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        generate_ea_settings.main(["--help"])

    assert excinfo.value.code == 0
    assert "Generate safe execution-disabled" in capsys.readouterr().out


def test_trial_micro_execution_preset_generates_required_set_files(tmp_path: Path) -> None:
    output = tmp_path / "trial_micro.set"
    result = generate_settings_artifacts(
        output_path=output,
        preset_name=TRIAL_MICRO_EXECUTION_PRESET,
        approval_metadata=ApprovalMetadata(source_scan_pass_id="source-scan-pass-13-2"),
        overrides={
            "broker_time_validation_note": "broker server UTC offset manually verified"
        },
    )

    text = output.read_text(encoding="utf-8")
    summary = json.loads(Path(result.summary_json_path).read_text(encoding="utf-8"))
    summary_md = Path(result.summary_md_path).read_text(encoding="utf-8")

    assert result.status == "PASS"
    assert "AccountProgram=ACCOUNT_PROGRAM_TRIAL_RISK_FREE" in text
    assert "AccountStage=ACCOUNT_STAGE_TRIAL" in text
    assert "EnablePropChallengeMode=false" in text
    assert "EnableTrading=true" in text
    assert "EnableTrialExecution=true" in text
    assert f"ManualConfirmationText={TRIAL_EXECUTION_MANUAL_CONFIRMATION}" in text
    assert "AllowedSymbols=EURUSD" in text
    assert "BrokerServerUtcOffsetMinutes=120" in text
    assert (
        "BrokerTimeValidationNote=broker server UTC offset manually verified" in text
    )
    assert "UseSpreadFilter=true" in text
    assert "MaxSpreadPoints=30" in text
    assert "SpreadUnknownBlocksTrading=true" in text
    assert "MinHoldSeconds=180" in text
    assert "StopLossRequired=true" in text
    assert "RiskPerTradePct=0.25" in text
    assert "MaxRiskPerTradePct=0.50" in text
    assert "MaxTradesPerDay=1" in text
    assert "MaxOpenPositionsTotal=1" in text
    assert "MaxOpenPositionsPerSymbol=1" in text
    assert "LogThrottleSkips=false" in text
    assert "SourceScanPassId=source-scan-pass-13-2" in text
    assert summary["trial_micro_execution_preset"] is True
    assert summary["trial_execution_enabled"] is True
    assert summary["trading_enabled"] is True
    assert summary["source_scan_pass_id"] == "source-scan-pass-13-2"
    assert "Disable EnableTrialExecution immediately" in summary_md


def test_trial_micro_execution_preset_requires_source_scan_pass_id() -> None:
    with pytest.raises(EaSettingsError, match="SourceScanPassId|source scan PASS marker"):
        build_settings(
            preset_name=TRIAL_MICRO_EXECUTION_PRESET,
            overrides={
                "broker_time_validation_note": "broker server UTC offset manually verified"
            },
        )


def test_trial_micro_execution_preset_requires_broker_time_validation_note() -> None:
    with pytest.raises(EaSettingsError, match="BrokerTimeValidationNote"):
        build_settings(
            preset_name=TRIAL_MICRO_EXECUTION_PRESET,
            approval_metadata=ApprovalMetadata(source_scan_pass_id="scan-pass"),
        )


@pytest.mark.parametrize("program", ["Surge2Step", "Vanguard", "Custom"])
def test_trial_micro_execution_preset_refuses_non_trial_programs(program: str) -> None:
    with pytest.raises(EaSettingsError, match="TrialRiskFree|rules are unverified|Vanguard"):
        build_settings(
            preset_name=TRIAL_MICRO_EXECUTION_PRESET,
            account_program=program,
            approval_metadata=ApprovalMetadata(source_scan_pass_id="scan-pass"),
            overrides={
                "broker_time_validation_note": "broker server UTC offset manually verified"
            },
        )


@pytest.mark.parametrize("stage", ["MonitorOnly", "Challenge", "Verification", "Funded"])
def test_trial_micro_execution_preset_refuses_non_trial_stages(stage: str) -> None:
    with pytest.raises(EaSettingsError, match="Trial|protected stage"):
        build_settings(
            preset_name=TRIAL_MICRO_EXECUTION_PRESET,
            stage=stage,
            approval_metadata=ApprovalMetadata(source_scan_pass_id="scan-pass"),
            overrides={
                "broker_time_validation_note": "broker server UTC offset manually verified"
            },
        )


def test_generate_ea_settings_script_refuses_micro_preset_without_scan_id(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = generate_ea_settings.main(
        [
            "--preset",
            TRIAL_MICRO_EXECUTION_PRESET,
            "--json",
        ]
    )

    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "FAIL"
    assert (
        "SourceScanPassId" in payload["message"]
        or "source scan PASS marker" in payload["message"]
    )


def test_generate_ea_settings_script_generates_micro_preset_with_scan_id(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "trial_micro.set"
    code = generate_ea_settings.main(
        [
            "--preset",
            TRIAL_MICRO_EXECUTION_PRESET,
            "--source-scan-pass-id",
            "scan-pass-cli",
            "--broker-time-validation-note",
            "broker server UTC offset manually verified",
            "--output-path",
            str(output),
            "--json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert payload["settings"]["enable_trial_execution"] is True
    assert "EnableTrialExecution=true" in output.read_text(encoding="utf-8")

from __future__ import annotations

from pathlib import Path

import pytest

from trading_bot.mql5.models import ApprovalMetadata
from trading_bot.mql5.settings import (
    TRIAL_EXECUTION_MANUAL_CONFIRMATION,
    TRIAL_MICRO_EXECUTION_PRESET,
    EaSettingsError,
    build_settings,
    render_set_file,
)

ROOT = Path(__file__).resolve().parents[1]
EA_SOURCE = (
    ROOT
    / "mql5"
    / "Experts"
    / "UpcomersNYSessionPropBot"
    / "UpcomersNYSessionPropBot.mq5"
)
CONFIG = ROOT / "mql5" / "Include" / "UpcomersNYSessionPropBot" / "Config.mqh"
TRIAL_EXECUTION = (
    ROOT / "mql5" / "Include" / "UpcomersNYSessionPropBot" / "TrialExecution.mqh"
)
TESTER_EXECUTION = (
    ROOT / "mql5" / "Include" / "UpcomersNYSessionPropBot" / "TesterExecution.mqh"
)

BROKER_TIME_NOTE = "broker server UTC offset manually verified against UTC before attach"


def test_generated_trial_micro_settings_pass_startup_gate_inputs() -> None:
    settings = build_settings(
        preset_name=TRIAL_MICRO_EXECUTION_PRESET,
        approval_metadata=ApprovalMetadata(source_scan_pass_id="phase13_3_scan_pass"),
        overrides={"broker_time_validation_note": BROKER_TIME_NOTE},
    )
    text = render_set_file(settings)

    assert "AccountProgram=ACCOUNT_PROGRAM_TRIAL_RISK_FREE" in text
    assert "AccountStage=ACCOUNT_STAGE_TRIAL" in text
    assert "EnableTrading=true" in text
    assert "EnableTrialExecution=true" in text
    assert "EnablePropChallengeMode=false" in text
    assert f"ManualConfirmationText={TRIAL_EXECUTION_MANUAL_CONFIRMATION}" in text
    assert "SourceScanPassId=phase13_3_scan_pass" in text
    assert "AllowedSymbols=EURUSD" in text
    assert "RequireBrokerTimeValidation=true" in text
    assert f"BrokerTimeValidationNote={BROKER_TIME_NOTE}" in text
    assert "PropDayResetTimezone=UNCONFIRMED_CONSERVATIVE" in text
    assert settings.approval_metadata.human_approval_id == ""
    assert settings.approval_metadata.final_audit_package_id == ""
    assert settings.approval_metadata.trial_evidence_id == ""
    assert settings.approval_metadata.account_program_rules_review_id == ""
    assert settings.approval_metadata.dynamic_risk_shield_confirmation_id == ""


def test_missing_source_scan_pass_id_fails_with_explicit_gate_name() -> None:
    with pytest.raises(EaSettingsError, match="SourceScanPassId|source scan PASS marker"):
        build_settings(
            preset_name=TRIAL_MICRO_EXECUTION_PRESET,
            overrides={"broker_time_validation_note": BROKER_TIME_NOTE},
        )

    ea_text = EA_SOURCE.read_text(encoding="utf-8")
    assert '"SOURCE_SCAN_PASS_ID"' in ea_text
    assert "GATE_FAIL_%s" in ea_text


def test_missing_broker_time_note_is_root_cause_gate() -> None:
    with pytest.raises(EaSettingsError, match="BrokerTimeValidationNote"):
        build_settings(
            preset_name=TRIAL_MICRO_EXECUTION_PRESET,
            approval_metadata=ApprovalMetadata(source_scan_pass_id="scan-pass"),
        )

    config_text = CONFIG.read_text(encoding="utf-8")
    ea_text = EA_SOURCE.read_text(encoding="utf-8")
    assert "Trial execution requires BrokerTimeValidationNote" in config_text
    assert '"BROKER_TIME_VALIDATION_NOTE"' in ea_text
    assert "TrialRiskFreeMicroExecution" in ea_text


def test_monitor_only_stage_with_trial_execution_fails_with_explicit_gate_name() -> None:
    with pytest.raises(EaSettingsError, match="AccountStage Trial"):
        build_settings(
            preset_name=TRIAL_MICRO_EXECUTION_PRESET,
            stage="MonitorOnly",
            approval_metadata=ApprovalMetadata(source_scan_pass_id="scan-pass"),
            overrides={"broker_time_validation_note": BROKER_TIME_NOTE},
        )

    assert '"TRIAL_ACCOUNT_STAGE"' in EA_SOURCE.read_text(encoding="utf-8")


@pytest.mark.parametrize("program", ["Surge2Step", "Vanguard", "Custom"])
def test_trial_micro_preset_keeps_non_trial_programs_blocked(program: str) -> None:
    with pytest.raises(EaSettingsError, match="TrialRiskFree|rules are unverified|Vanguard"):
        build_settings(
            preset_name=TRIAL_MICRO_EXECUTION_PRESET,
            account_program=program,
            approval_metadata=ApprovalMetadata(source_scan_pass_id="scan-pass"),
            overrides={"broker_time_validation_note": BROKER_TIME_NOTE},
        )


@pytest.mark.parametrize("stage", ["Challenge", "Verification", "Funded"])
def test_trial_micro_preset_keeps_protected_stages_blocked(stage: str) -> None:
    with pytest.raises(EaSettingsError, match="AccountStage Trial|protected stage"):
        build_settings(
            preset_name=TRIAL_MICRO_EXECUTION_PRESET,
            stage=stage,
            approval_metadata=ApprovalMetadata(source_scan_pass_id="scan-pass"),
            overrides={"broker_time_validation_note": BROKER_TIME_NOTE},
        )


def test_trial_micro_does_not_require_protected_approval_ids() -> None:
    settings = build_settings(
        preset_name=TRIAL_MICRO_EXECUTION_PRESET,
        approval_metadata=ApprovalMetadata(source_scan_pass_id="scan-pass"),
        overrides={"broker_time_validation_note": BROKER_TIME_NOTE},
    )

    assert settings.enable_trial_execution is True
    assert settings.approval_metadata.human_approval_id == ""
    assert settings.approval_metadata.final_audit_package_id == ""
    assert settings.approval_metadata.trial_evidence_id == ""
    assert settings.approval_metadata.account_program_rules_review_id == ""
    assert settings.approval_metadata.dynamic_risk_shield_confirmation_id == ""


def test_no_order_calls_outside_isolated_execution_modules() -> None:
    for path in (ROOT / "mql5").rglob("*"):
        if path.suffix.lower() not in {".mq5", ".mqh"} or path in {
            TRIAL_EXECUTION,
            TESTER_EXECUTION,
        }:
            continue
        text = path.read_text(encoding="utf-8")
        assert "OrderSend" not in text
        assert "CTrade" not in text
        assert ".Buy(" not in text
        assert ".Sell(" not in text
        assert "PositionOpen" not in text

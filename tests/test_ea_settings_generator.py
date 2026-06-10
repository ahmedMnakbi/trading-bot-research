from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import generate_ea_settings
from trading_bot.mql5.models import ApprovalMetadata
from trading_bot.mql5.settings import (
    STRATEGY_TESTER_NYM15SR_NACUSD_PRESET,
    STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_PRESET,
    STRATEGY_TESTER_NYM15SR_PRESET,
    STRATEGY_TESTER_NYM15SR_SPCUSD_PRESET,
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


def test_nym15sr_preset_validates_and_generates_set_file(tmp_path: Path) -> None:
    output = tmp_path / "nym15sr.set"
    result = generate_settings_artifacts(
        output_path=output,
        preset_name=STRATEGY_TESTER_NYM15SR_PRESET,
        stage="MonitorOnly",
    )

    assert result.status == "PASS"
    text = output.read_text(encoding="utf-8")
    assert "StrategySelection=STRATEGY_NY_M15_SWEEP_RECLAIM" in text
    assert "EnableTrading=false" in text
    assert "EnableTrialExecution=false" in text
    assert "StrategyTesterExecutionMode=true" in text
    assert "NYM15SRNYOpenHour=9" in text
    assert "NYM15SRNYOpenMinute=30" in text
    assert "NYM15SRNYWindowEndHour=11" in text
    assert "NYM15SRNYWindowEndMinute=0" in text
    assert "NYM15SREMAPeriod=50" in text
    assert "NYM15SRMinCRTRangePoints=100.00" in text
    assert "NYM15SRMinSweepPoints=20.00" in text
    assert "NYM15SRStopBufferPoints=50.00" in text
    assert "NYM15SRTakeProfitR=2.00" in text
    assert "NYM15SRMaxBarsAfterSweep=12" in text
    assert "NYM15SRRequireM15DirectionAgreement=true" in text


def test_nym15sr_preset_uses_correct_strategy_selection() -> None:
    settings = build_settings(
        preset_name=STRATEGY_TESTER_NYM15SR_PRESET,
        stage="MonitorOnly",
    )
    assert settings.strategy_selection == "STRATEGY_NY_M15_SWEEP_RECLAIM"


def test_nym15sr_preset_no_live_or_trial_execution() -> None:
    settings = build_settings(
        preset_name=STRATEGY_TESTER_NYM15SR_PRESET,
        stage="MonitorOnly",
    )
    assert settings.enable_trading is False
    assert settings.enable_trial_execution is False
    assert settings.strategy_tester_execution_mode is True
    assert settings.enable_prop_challenge_mode is False


def test_nym15sr_preset_default_fields_match_spec() -> None:
    settings = build_settings(
        preset_name=STRATEGY_TESTER_NYM15SR_PRESET,
        stage="MonitorOnly",
    )
    assert settings.nym15sr_ny_open_hour == 9
    assert settings.nym15sr_ny_open_minute == 30
    assert settings.nym15sr_ny_window_end_hour == 11
    assert settings.nym15sr_ny_window_end_minute == 0
    assert settings.nym15sr_ema_period == 50
    assert settings.nym15sr_min_crt_range_points == 100.0
    assert settings.nym15sr_min_sweep_points == 20.0
    assert settings.nym15sr_stop_buffer_points == 50.0
    assert settings.nym15sr_take_profit_r == 2.0
    assert settings.nym15sr_max_bars_after_sweep == 12
    assert settings.nym15sr_require_m15_direction_agreement is True


def test_generate_ea_settings_script_generates_nym15sr_preset(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "nym15sr.set"
    code = generate_ea_settings.main(
        [
            "--preset",
            STRATEGY_TESTER_NYM15SR_PRESET,
            "--output-path",
            str(output),
            "--json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert payload["settings"]["strategy_selection"] == "STRATEGY_NY_M15_SWEEP_RECLAIM"
    text = output.read_text(encoding="utf-8")
    assert "StrategySelection=STRATEGY_NY_M15_SWEEP_RECLAIM" in text
    assert "EnableTrading=false" in text
    assert "EnableTrialExecution=false" in text
    assert "NYM15SRNYOpenHour=9" in text
    assert "NYM15SRMaxBarsAfterSweep=12" in text


@pytest.mark.parametrize(
    ("preset", "symbol"),
    [
        (STRATEGY_TESTER_NYM15SR_NACUSD_PRESET, "NACUSD.c"),
        (STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_PRESET, "NACUSD.c"),
        (STRATEGY_TESTER_NYM15SR_SPCUSD_PRESET, "SPCUSD.c"),
    ],
)
def test_index_nym15sr_presets_validate_and_generate_set_files(
    tmp_path: Path,
    preset: str,
    symbol: str,
) -> None:
    output = tmp_path / f"{preset}.set"
    result = generate_settings_artifacts(
        output_path=output,
        preset_name=preset,
        stage="MonitorOnly",
    )

    assert result.status == "PASS"
    assert result.settings.allowed_symbols == symbol
    assert result.settings.strategy_timeframe == "PERIOD_M5"
    assert result.settings.strategy_selection == "STRATEGY_NY_M15_SWEEP_RECLAIM"
    assert result.settings.enable_trading is False
    assert result.settings.enable_trial_execution is False
    assert result.settings.strategy_tester_execution_mode is True
    assert result.settings.nym15sr_require_m15_direction_agreement is (
        preset != STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_PRESET
    )

    text = output.read_text(encoding="utf-8")
    assert f"AllowedSymbols={symbol}" in text
    assert "StrategyTimeframe=PERIOD_M5" in text
    assert "StrategySelection=STRATEGY_NY_M15_SWEEP_RECLAIM" in text
    assert "EnableTrading=false" in text
    assert "EnableTrialExecution=false" in text
    assert "StrategyTesterExecutionMode=true" in text
    assert "NYM15SRNYOpenHour=9" in text
    assert "NYM15SRNYOpenMinute=30" in text
    assert "NYM15SRNYWindowEndHour=11" in text
    assert "NYM15SRNYWindowEndMinute=0" in text
    assert "NYM15SREMAPeriod=50" in text
    expected_values = (
        {
            "MaxSpreadPoints": "1000",
            "NYM15SRMinCRTRangePoints": "3000.00",
            "NYM15SRMinSweepPoints": "500.00",
            "NYM15SRStopBufferPoints": "500.00",
        }
        if symbol == "NACUSD.c"
        else {
            "MaxSpreadPoints": "500",
            "NYM15SRMinCRTRangePoints": "1000.00",
            "NYM15SRMinSweepPoints": "150.00",
            "NYM15SRStopBufferPoints": "250.00",
        }
    )
    for key, value in expected_values.items():
        assert f"{key}={value}" in text
    assert "NYM15SRTakeProfitR=2.00" in text
    assert "NYM15SRMaxBarsAfterSweep=12" in text
    expected_agreement = (
        "false"
        if preset == STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_PRESET
        else "true"
    )
    assert f"NYM15SRRequireM15DirectionAgreement={expected_agreement}" in text
    assert "not optimized index values" in text


@pytest.mark.parametrize(
    ("preset", "symbol"),
    [
        (STRATEGY_TESTER_NYM15SR_NACUSD_PRESET, "NACUSD.c"),
        (STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_PRESET, "NACUSD.c"),
        (STRATEGY_TESTER_NYM15SR_SPCUSD_PRESET, "SPCUSD.c"),
    ],
)
def test_generate_ea_settings_script_generates_index_nym15sr_presets(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    preset: str,
    symbol: str,
) -> None:
    output = tmp_path / f"{preset}.set"
    code = generate_ea_settings.main(
        [
            "--preset",
            preset,
            "--output-path",
            str(output),
            "--json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert payload["settings"]["allowed_symbols"] == symbol
    assert payload["settings"]["strategy_timeframe"] == "PERIOD_M5"
    assert payload["settings"]["strategy_selection"] == "STRATEGY_NY_M15_SWEEP_RECLAIM"
    text = output.read_text(encoding="utf-8")
    assert f"AllowedSymbols={symbol}" in text
    assert "StrategyTesterExecutionMode=true" in text
    assert "NYM15SRMaxBarsAfterSweep=12" in text


def test_nacusd_nym15sr_preset_generates_ready_to_run_values(tmp_path: Path) -> None:
    output = tmp_path / "nacusd.set"
    result = generate_settings_artifacts(
        output_path=output,
        preset_name=STRATEGY_TESTER_NYM15SR_NACUSD_PRESET,
        stage="MonitorOnly",
    )

    assert result.status == "PASS"
    text = output.read_text(encoding="utf-8")
    assert "AllowedSymbols=NACUSD.c" in text
    assert "StrategySelection=STRATEGY_NY_M15_SWEEP_RECLAIM" in text
    assert "EnableTrading=false" in text
    assert "EnableTrialExecution=false" in text
    assert "StrategyTesterExecutionMode=true" in text
    assert "MaxSpreadPoints=1000" in text
    assert "NYM15SRNYOpenHour=9" in text
    assert "NYM15SRNYOpenMinute=30" in text
    assert "NYM15SRNYWindowEndHour=11" in text
    assert "NYM15SRNYWindowEndMinute=0" in text
    assert "NYM15SREMAPeriod=50" in text
    assert "NYM15SRMinCRTRangePoints=3000.00" in text
    assert "NYM15SRMinSweepPoints=500.00" in text
    assert "NYM15SRStopBufferPoints=500.00" in text
    assert "NYM15SRTakeProfitR=2.00" in text
    assert "NYM15SRMaxBarsAfterSweep=12" in text
    assert "NYM15SRRequireM15DirectionAgreement=true" in text
    assert "NACUSD.c" in text
    assert "NQCUSD.c" not in text


def test_nacusd_relaxed_m15_direction_variant_is_tester_only(
    tmp_path: Path,
) -> None:
    output = tmp_path / "nacusd_relaxed_m15.set"
    result = generate_settings_artifacts(
        output_path=output,
        preset_name=STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_PRESET,
        stage="MonitorOnly",
    )

    assert result.status == "PASS"
    assert result.settings.allowed_symbols == "NACUSD.c"
    assert result.settings.enable_trading is False
    assert result.settings.enable_trial_execution is False
    assert result.settings.strategy_tester_execution_mode is True
    assert result.settings.nym15sr_require_m15_direction_agreement is False

    text = output.read_text(encoding="utf-8")
    assert "AllowedSymbols=NACUSD.c" in text
    assert "StrategySelection=STRATEGY_NY_M15_SWEEP_RECLAIM" in text
    assert "StrategyTimeframe=PERIOD_M5" in text
    assert "EnableTrading=false" in text
    assert "EnableTrialExecution=false" in text
    assert "StrategyTesterExecutionMode=true" in text
    assert "MaxSpreadPoints=1000" in text
    assert "NYM15SRMinCRTRangePoints=3000.00" in text
    assert "NYM15SRMinSweepPoints=500.00" in text
    assert "NYM15SRStopBufferPoints=500.00" in text
    assert "NYM15SRRequireM15DirectionAgreement=false" in text
    assert "relaxes the first M15 candle direction agreement filter" in text

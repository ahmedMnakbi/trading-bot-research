from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from trading_bot.mql5.models import (
    ApprovalMetadata,
    EaSettings,
    GeneratedSettingsArtifacts,
    to_jsonable,
)

PROTECTED_STAGES = {"Challenge", "Verification", "Funded"}
PROTECTED_PROGRAMS = {"Vanguard", "Surge2Step", "Custom"}
RULE_UNVERIFIED_PROGRAMS = {"Surge2Step", "Custom"}
ACCOUNT_PROGRAM_ENUMS = {
    "TrialRiskFree": "ACCOUNT_PROGRAM_TRIAL_RISK_FREE",
    "Vanguard": "ACCOUNT_PROGRAM_VANGUARD",
    "Surge2Step": "ACCOUNT_PROGRAM_SURGE_2_STEP",
    "Custom": "ACCOUNT_PROGRAM_CUSTOM",
}
ACCOUNT_STAGE_ENUMS = {
    "MonitorOnly": "ACCOUNT_STAGE_MONITOR_ONLY",
    "Trial": "ACCOUNT_STAGE_TRIAL",
    "Challenge": "ACCOUNT_STAGE_CHALLENGE",
    "Verification": "ACCOUNT_STAGE_VERIFICATION",
    "Funded": "ACCOUNT_STAGE_FUNDED",
}
REQUIRED_MANUAL_CONFIRMATION = "I ACCEPT MONITOR ONLY PHASE 5 - NO TRADING"
TRIAL_EXECUTION_MANUAL_CONFIRMATION = "I_ACCEPT_TRIAL_RISK_FREE_EXECUTION_ONLY"
TRIAL_MICRO_EXECUTION_PRESET = "trial-risk-free-eurusd-micro-execution"
STRATEGY_TESTER_ORB_PRESET = "strategy-tester-eurusd-m5-orb"
STRATEGY_TESTER_VWAP_PRESET = "strategy-tester-eurusd-m5-vwap"
STRATEGY_TESTER_NYM15SR_PRESET = "strategy-tester-eurusd-m5-ny-m15-sweep-reclaim"
STRATEGY_TESTER_NYM15SR_NACUSD_PRESET = (
    "strategy-tester-nacusd-c-m5-ny-m15-sweep-reclaim"
)
STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_PRESET = (
    "strategy-tester-nacusd-c-m5-ny-m15-sweep-reclaim-relaxed-m15-direction"
)
STRATEGY_TESTER_NYM15SR_NACUSD_RECLAIM_HOLD_PRESET = (
    "strategy-tester-nacusd-c-m5-ny-m15-sweep-reclaim-reclaim-hold-entry"
)
STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_RECLAIM_HOLD_PRESET = (
    "strategy-tester-nacusd-c-m5-ny-m15-sweep-reclaim-relaxed-m15-reclaim-hold-entry"
)
STRATEGY_TESTER_NYM15SR_SPCUSD_PRESET = (
    "strategy-tester-spcusd-c-m5-ny-m15-sweep-reclaim"
)
APPROVED_STRATEGY_TESTER_SYMBOLS = {"EURUSD", "NACUSD.c", "SPCUSD.c"}
STRATEGY_TESTER_PRESETS = {
    STRATEGY_TESTER_ORB_PRESET,
    STRATEGY_TESTER_VWAP_PRESET,
    STRATEGY_TESTER_NYM15SR_PRESET,
    STRATEGY_TESTER_NYM15SR_NACUSD_PRESET,
    STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_PRESET,
    STRATEGY_TESTER_NYM15SR_NACUSD_RECLAIM_HOLD_PRESET,
    STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_RECLAIM_HOLD_PRESET,
    STRATEGY_TESTER_NYM15SR_SPCUSD_PRESET,
}
STRATEGY_TESTER_PRESET_SYMBOLS = {
    STRATEGY_TESTER_ORB_PRESET: "EURUSD",
    STRATEGY_TESTER_VWAP_PRESET: "EURUSD",
    STRATEGY_TESTER_NYM15SR_PRESET: "EURUSD",
    STRATEGY_TESTER_NYM15SR_NACUSD_PRESET: "NACUSD.c",
    STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_PRESET: "NACUSD.c",
    STRATEGY_TESTER_NYM15SR_NACUSD_RECLAIM_HOLD_PRESET: "NACUSD.c",
    STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_RECLAIM_HOLD_PRESET: "NACUSD.c",
    STRATEGY_TESTER_NYM15SR_SPCUSD_PRESET: "SPCUSD.c",
}
STRATEGY_TESTER_PRESET_MAX_SPREAD_POINTS = {
    STRATEGY_TESTER_ORB_PRESET: 30,
    STRATEGY_TESTER_VWAP_PRESET: 30,
    STRATEGY_TESTER_NYM15SR_PRESET: 30,
    STRATEGY_TESTER_NYM15SR_NACUSD_PRESET: 1000,
    STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_PRESET: 1000,
    STRATEGY_TESTER_NYM15SR_NACUSD_RECLAIM_HOLD_PRESET: 1000,
    STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_RECLAIM_HOLD_PRESET: 1000,
    STRATEGY_TESTER_NYM15SR_SPCUSD_PRESET: 500,
}

TRIAL_MICRO_EXECUTION_OVERRIDES: dict[str, Any] = {
    "enable_trading": True,
    "enable_trial_execution": True,
    "enable_prop_challenge_mode": False,
    "require_manual_confirmation_text": True,
    "manual_confirmation_text": TRIAL_EXECUTION_MANUAL_CONFIRMATION,
    "allowed_symbols": "EURUSD",
    "broker_server_utc_offset_minutes": 120,
    "use_spread_filter": True,
    "max_spread_points": 30,
    "spread_unknown_blocks_trading": True,
    "min_hold_seconds": 180,
    "stop_loss_required": True,
    "risk_per_trade_pct": 0.25,
    "max_risk_per_trade_pct": 0.50,
    "max_trades_per_day": 1,
    "max_open_positions_total": 1,
    "max_open_positions_per_symbol": 1,
    "log_throttle_skips": False,
}

STRATEGY_TESTER_COMMON_OVERRIDES: dict[str, Any] = {
    "enable_trading": False,
    "enable_trial_execution": False,
    "strategy_tester_execution_mode": True,
    "enable_prop_challenge_mode": False,
    "require_manual_confirmation_text": True,
    "manual_confirmation_text": "",
    "allowed_symbols": "EURUSD",
    "strategy_timeframe": "PERIOD_M5",
    "use_spread_filter": True,
    "max_spread_points": 30,
    "spread_unknown_blocks_trading": True,
    "min_hold_seconds": 180,
    "stop_loss_required": True,
    "risk_per_trade_pct": 0.25,
    "max_risk_per_trade_pct": 0.50,
    "max_trades_per_day": 1,
    "max_open_positions_total": 1,
    "max_open_positions_per_symbol": 1,
    "broker_server_utc_offset_minutes": 120,
    "broker_time_validation_note": (
        "Strategy Tester research preset; verify broker UTC offset before interpreting "
        "session-based results"
    ),
    "log_throttle_skips": False,
}

STRATEGY_TESTER_PRESET_OVERRIDES: dict[str, dict[str, Any]] = {
    STRATEGY_TESTER_ORB_PRESET: {
        **STRATEGY_TESTER_COMMON_OVERRIDES,
        "strategy_selection": "STRATEGY_OPENING_RANGE_BREAKOUT",
    },
    STRATEGY_TESTER_VWAP_PRESET: {
        **STRATEGY_TESTER_COMMON_OVERRIDES,
        "strategy_selection": "STRATEGY_VWAP_TREND_CONTINUATION",
    },
    STRATEGY_TESTER_NYM15SR_PRESET: {
        **STRATEGY_TESTER_COMMON_OVERRIDES,
        "strategy_selection": "STRATEGY_NY_M15_SWEEP_RECLAIM",
    },
    STRATEGY_TESTER_NYM15SR_NACUSD_PRESET: {
        **STRATEGY_TESTER_COMMON_OVERRIDES,
        "allowed_symbols": "NACUSD.c",
        "strategy_selection": "STRATEGY_NY_M15_SWEEP_RECLAIM",
        "max_spread_points": 1000,
        "nym15sr_min_crt_range_points": 3000.0,
        "nym15sr_min_sweep_points": 500.0,
        "nym15sr_stop_buffer_points": 500.0,
        "broker_time_validation_note": (
            "Strategy Tester research preset for NACUSD.c; verify broker UTC offset, "
            "point size, tick value, and spread in MT5 Symbol Specification before "
            "interpreting index results. NYM15SR parameters are initial defaults, not "
            "optimized index values."
        ),
    },
    STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_PRESET: {
        **STRATEGY_TESTER_COMMON_OVERRIDES,
        "allowed_symbols": "NACUSD.c",
        "strategy_selection": "STRATEGY_NY_M15_SWEEP_RECLAIM",
        "max_spread_points": 1000,
        "nym15sr_min_crt_range_points": 3000.0,
        "nym15sr_min_sweep_points": 500.0,
        "nym15sr_stop_buffer_points": 500.0,
        "nym15sr_require_m15_direction_agreement": False,
        "broker_time_validation_note": (
            "Strategy Tester research variant for NACUSD.c; relaxes the first "
            "M15 candle direction agreement filter while preserving the H1 EMA "
            "trend direction. Verify broker UTC offset, point size, tick value, "
            "and spread in MT5 Symbol Specification before interpreting index "
            "results. NYM15SR parameters are research defaults, not optimized "
            "index values."
        ),
    },
    STRATEGY_TESTER_NYM15SR_NACUSD_RECLAIM_HOLD_PRESET: {
        **STRATEGY_TESTER_COMMON_OVERRIDES,
        "allowed_symbols": "NACUSD.c",
        "strategy_selection": "STRATEGY_NY_M15_SWEEP_RECLAIM",
        "max_spread_points": 1000,
        "nym15sr_min_crt_range_points": 3000.0,
        "nym15sr_min_sweep_points": 500.0,
        "nym15sr_stop_buffer_points": 500.0,
        "nym15sr_require_reclaim_breakout_entry": False,
        "broker_time_validation_note": (
            "Strategy Tester research variant for NACUSD.c; keeps first M15 "
            "direction agreement strict but relaxes entry after reclaim to a "
            "later closed M5 candle that remains on the reclaimed side of the "
            "M15 level. Verify broker UTC offset, point size, tick value, and "
            "spread in MT5 Symbol Specification before interpreting index "
            "results. NYM15SR parameters are research defaults, not optimized "
            "index values."
        ),
    },
    STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_RECLAIM_HOLD_PRESET: {
        **STRATEGY_TESTER_COMMON_OVERRIDES,
        "allowed_symbols": "NACUSD.c",
        "strategy_selection": "STRATEGY_NY_M15_SWEEP_RECLAIM",
        "max_spread_points": 1000,
        "nym15sr_min_crt_range_points": 3000.0,
        "nym15sr_min_sweep_points": 500.0,
        "nym15sr_stop_buffer_points": 500.0,
        "nym15sr_require_m15_direction_agreement": False,
        "nym15sr_require_reclaim_breakout_entry": False,
        "broker_time_validation_note": (
            "Strategy Tester research variant for NACUSD.c; relaxes the first "
            "M15 candle direction agreement filter and relaxes entry after "
            "reclaim to a later closed M5 candle that remains on the reclaimed "
            "side of the M15 level. H1 EMA trend still controls trade "
            "direction. Verify broker UTC offset, point size, tick value, and "
            "spread in MT5 Symbol Specification before interpreting index "
            "results. NYM15SR parameters are research defaults, not optimized "
            "index values."
        ),
    },
    STRATEGY_TESTER_NYM15SR_SPCUSD_PRESET: {
        **STRATEGY_TESTER_COMMON_OVERRIDES,
        "allowed_symbols": "SPCUSD.c",
        "strategy_selection": "STRATEGY_NY_M15_SWEEP_RECLAIM",
        "max_spread_points": 500,
        "nym15sr_min_crt_range_points": 1000.0,
        "nym15sr_min_sweep_points": 150.0,
        "nym15sr_stop_buffer_points": 250.0,
        "broker_time_validation_note": (
            "Strategy Tester research preset for SPCUSD.c; verify broker UTC offset, "
            "point size, tick value, and spread in MT5 Symbol Specification before "
            "interpreting index results. NYM15SR parameters are initial defaults, not "
            "optimized index values."
        ),
    },
}


class EaSettingsError(ValueError):
    """Raised when an EA settings preset is unsafe."""


def build_settings(
    *,
    preset_name: str = "trial-monitor-only",
    account_program: str = "TrialRiskFree",
    stage: str = "Trial",
    approval_metadata: ApprovalMetadata | None = None,
    overrides: dict[str, Any] | None = None,
) -> EaSettings:
    metadata = approval_metadata or ApprovalMetadata()
    settings = EaSettings(
        preset_name=preset_name,
        account_program=account_program,
        account_stage=stage,
        approval_metadata=metadata,
    )
    if preset_name == TRIAL_MICRO_EXECUTION_PRESET:
        settings = replace(settings, **TRIAL_MICRO_EXECUTION_OVERRIDES)
    elif preset_name in STRATEGY_TESTER_PRESETS:
        settings = replace(settings, **STRATEGY_TESTER_PRESET_OVERRIDES[preset_name])
    if overrides:
        settings = replace(settings, **overrides)
    validate_settings(settings)
    return settings


def validate_settings(settings: EaSettings) -> None:
    failures: list[str] = []
    if settings.account_stage not in ACCOUNT_STAGE_ENUMS:
        failures.append(f"unsupported account stage: {settings.account_stage}")
    if settings.account_program not in ACCOUNT_PROGRAM_ENUMS:
        failures.append(f"unsupported account program: {settings.account_program}")
    if settings.enable_trading and not settings.enable_trial_execution and (
        not settings.require_manual_confirmation_text
        or settings.manual_confirmation_text != REQUIRED_MANUAL_CONFIRMATION
    ):
        failures.append("trading enabled without strict manual confirmation")
    if settings.enable_trial_execution:
        if not settings.enable_trading:
            failures.append("trial execution requires trading enabled")
        if settings.account_program != "TrialRiskFree":
            failures.append("trial execution requires AccountProgram TrialRiskFree")
        if settings.account_stage != "Trial":
            failures.append("trial execution requires AccountStage Trial")
        if settings.enable_prop_challenge_mode:
            failures.append("trial execution requires prop challenge mode disabled")
        if (
            not settings.require_manual_confirmation_text
            or settings.manual_confirmation_text != TRIAL_EXECUTION_MANUAL_CONFIRMATION
        ):
            failures.append("trial execution requires exact manual confirmation")
        if not settings.approval_metadata.source_scan_pass_id:
            failures.append("trial execution requires source scan PASS marker")
        if settings.risk_per_trade_pct > 0.25:
            failures.append("trial execution requires risk per trade <= 0.25")
        if settings.max_open_positions_total != 1 or settings.max_open_positions_per_symbol != 1:
            failures.append("trial execution requires position caps of one")
        if settings.max_trades_per_day != 1:
            failures.append("trial execution requires max trades per day of one")
        if settings.max_server_messages_per_day > 500:
            failures.append("trial execution requires max server messages per day <= 500")
        if settings.allowed_symbols != "EURUSD":
            failures.append("trial execution requires AllowedSymbols=EURUSD")
        if not settings.use_spread_filter:
            failures.append("trial execution requires spread filter enabled")
        if not settings.require_broker_time_validation:
            failures.append("trial execution requires broker time validation enabled")
        if not settings.broker_time_validation_note:
            failures.append(
                "trial execution requires BrokerTimeValidationNote after verifying "
                "BrokerServerUtcOffsetMinutes"
            )
    if settings.strategy_tester_execution_mode:
        if settings.enable_trading:
            failures.append("Strategy Tester execution requires EnableTrading=false")
        if settings.enable_trial_execution:
            failures.append(
                "Strategy Tester execution is separate from EnableTrialExecution"
            )
        if settings.enable_prop_challenge_mode:
            failures.append("Strategy Tester execution requires prop challenge mode disabled")
        if settings.account_program != "TrialRiskFree":
            failures.append("Strategy Tester execution requires AccountProgram TrialRiskFree")
        if settings.account_stage != "MonitorOnly":
            failures.append("Strategy Tester execution requires AccountStage MonitorOnly")
        if settings.allowed_symbols not in APPROVED_STRATEGY_TESTER_SYMBOLS:
            failures.append(
                "Strategy Tester execution requires AllowedSymbols to be one approved "
                "research tester symbol: EURUSD, NACUSD.c, or SPCUSD.c"
            )
        if not settings.stop_loss_required:
            failures.append("Strategy Tester execution requires StopLossRequired=true")
        if settings.min_hold_seconds < 180:
            failures.append("Strategy Tester execution requires MinHoldSeconds>=180")
        if settings.risk_per_trade_pct > 0.25:
            failures.append("Strategy Tester execution requires risk per trade <= 0.25")
        if settings.max_risk_per_trade_pct > 0.50:
            failures.append("Strategy Tester execution requires max risk per trade <= 0.50")
        if (
            settings.max_open_positions_total != 1
            or settings.max_open_positions_per_symbol != 1
        ):
            failures.append("Strategy Tester execution requires position caps of one")
        if settings.max_trades_per_day != 1:
            failures.append("Strategy Tester execution requires max trades per day of one")
        if not settings.use_spread_filter:
            failures.append("Strategy Tester execution requires spread filter enabled")
    if settings.preset_name in STRATEGY_TESTER_PRESETS:
        _validate_strategy_tester_preset(settings, failures)
    if settings.preset_name == TRIAL_MICRO_EXECUTION_PRESET:
        _validate_trial_micro_execution_preset(settings, failures)
    if settings.enable_prop_challenge_mode and settings.account_stage not in PROTECTED_STAGES:
        failures.append("prop challenge mode requires Challenge, Verification, or Funded stage")
    if settings.account_stage in PROTECTED_STAGES:
        missing = settings.approval_metadata.missing_for_protected_stage()
        if missing:
            failures.append(f"protected stage missing approval metadata: {', '.join(missing)}")
    if settings.account_program in RULE_UNVERIFIED_PROGRAMS and (
        settings.enable_trading
        or settings.enable_prop_challenge_mode
        or settings.strategy_tester_execution_mode
        or settings.account_stage in PROTECTED_STAGES
    ):
        failures.append(
            f"{settings.account_program} rules are unverified; protected or active use is blocked"
        )
    if settings.account_program == "Vanguard" and (
        settings.enable_trading
        or settings.enable_prop_challenge_mode
        or settings.strategy_tester_execution_mode
        or settings.account_stage in PROTECTED_STAGES
    ):
        missing = settings.approval_metadata.missing_for_protected_stage()
        if missing:
            failures.append(
                "Vanguard requires exact rules, trial evidence, audit package, and "
                f"approval metadata: {', '.join(missing)}"
            )
    if settings.max_daily_loss_hard_pct >= 4.0:
        failures.append("daily hard loss must stay below 4.0")
    if settings.max_overall_loss_hard_pct >= 7.0:
        failures.append("overall hard loss must stay below 7.0")
    if settings.max_risk_per_trade_pct > 0.50:
        failures.append("max risk per trade must be <= 0.50")
    if settings.min_hold_seconds < 180:
        failures.append("min hold seconds must be >= 180")
    if not settings.stop_loss_required:
        failures.append("stop loss must be required")
    if settings.max_trades_per_day > 20:
        failures.append("max trades per day must be <= 20")
    if settings.max_server_messages_per_day > 2000:
        failures.append("max server messages per day must be <= 2000")
    if not settings.allowed_symbols:
        failures.append("allowed symbols must not be empty")
    if settings.trial_execution_magic_number <= 0:
        failures.append("trial execution magic number must be positive")
    if settings.allow_grid:
        failures.append("grid flag must remain false")
    if settings.allow_martingale:
        failures.append("martingale flag must remain false")
    if settings.allow_averaging_down:
        failures.append("averaging-down flag must remain false")
    if settings.allow_hft:
        failures.append("HFT flag must remain false")
    if settings.allow_arbitrage:
        failures.append("arbitrage flag must remain false")
    if settings.allow_copy_trading:
        failures.append("copy-trading flag must remain false")
    if settings.allow_scalping_under_2_minutes:
        failures.append("sub-2-minute scalping flag must remain false")
    if settings.max_signals_per_strategy_per_session <= 0:
        failures.append("max signals per strategy/session must be positive")
    if settings.broker_time_mode != "BROKER_TIME_MANUAL_UTC_OFFSET":
        failures.append("broker time mode must use explicit manual UTC offset")
    if not -720 <= settings.broker_server_utc_offset_minutes <= 840:
        failures.append("broker server UTC offset minutes must be between -720 and 840")
    if settings.max_spread_points <= 0:
        failures.append("max spread points must be positive")
    if not settings.spread_unknown_blocks_trading:
        failures.append("unknown spread must block monitor signals")
    if settings.evaluation_mode not in {"EVALUATION_ON_NEW_CLOSED_BAR", "EVALUATION_TIMER"}:
        failures.append("unsupported evaluation mode")
    if settings.min_evaluation_seconds < 1:
        failures.append("minimum evaluation seconds must be positive")
    if failures:
        raise EaSettingsError("; ".join(failures))


def _validate_trial_micro_execution_preset(
    settings: EaSettings,
    failures: list[str],
) -> None:
    expected_values: dict[str, object] = {
        "account_program": "TrialRiskFree",
        "account_stage": "Trial",
        "enable_prop_challenge_mode": False,
        "enable_trading": True,
        "enable_trial_execution": True,
        "manual_confirmation_text": TRIAL_EXECUTION_MANUAL_CONFIRMATION,
        "allowed_symbols": "EURUSD",
        "broker_server_utc_offset_minutes": 120,
        "use_spread_filter": True,
        "max_spread_points": 30,
        "spread_unknown_blocks_trading": True,
        "min_hold_seconds": 180,
        "stop_loss_required": True,
        "risk_per_trade_pct": 0.25,
        "max_risk_per_trade_pct": 0.50,
        "max_trades_per_day": 1,
        "max_open_positions_total": 1,
        "max_open_positions_per_symbol": 1,
        "require_broker_time_validation": True,
        "log_throttle_skips": False,
    }
    for field_name, expected in expected_values.items():
        actual = getattr(settings, field_name)
        if actual != expected:
            failures.append(
                f"{TRIAL_MICRO_EXECUTION_PRESET} requires {field_name}={expected!r}"
            )
    if not settings.approval_metadata.source_scan_pass_id:
        failures.append(
            f"{TRIAL_MICRO_EXECUTION_PRESET} requires non-empty SourceScanPassId"
        )
    if not settings.broker_time_validation_note:
        failures.append(
            f"{TRIAL_MICRO_EXECUTION_PRESET} requires non-empty BrokerTimeValidationNote"
        )


def _validate_strategy_tester_preset(
    settings: EaSettings,
    failures: list[str],
) -> None:
    expected_values: dict[str, object] = {
        "account_program": "TrialRiskFree",
        "account_stage": "MonitorOnly",
        "enable_trading": False,
        "enable_trial_execution": False,
        "strategy_tester_execution_mode": True,
        "enable_prop_challenge_mode": False,
        "allowed_symbols": STRATEGY_TESTER_PRESET_SYMBOLS[settings.preset_name],
        "strategy_timeframe": "PERIOD_M5",
        "use_spread_filter": True,
        "max_spread_points": STRATEGY_TESTER_PRESET_MAX_SPREAD_POINTS[
            settings.preset_name
        ],
        "spread_unknown_blocks_trading": True,
        "min_hold_seconds": 180,
        "stop_loss_required": True,
        "risk_per_trade_pct": 0.25,
        "max_risk_per_trade_pct": 0.50,
        "max_trades_per_day": 1,
        "max_open_positions_total": 1,
        "max_open_positions_per_symbol": 1,
        "log_throttle_skips": False,
    }
    _preset_strategy_map = {
        STRATEGY_TESTER_ORB_PRESET: "STRATEGY_OPENING_RANGE_BREAKOUT",
        STRATEGY_TESTER_VWAP_PRESET: "STRATEGY_VWAP_TREND_CONTINUATION",
        STRATEGY_TESTER_NYM15SR_PRESET: "STRATEGY_NY_M15_SWEEP_RECLAIM",
        STRATEGY_TESTER_NYM15SR_NACUSD_PRESET: "STRATEGY_NY_M15_SWEEP_RECLAIM",
        STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_PRESET: (
            "STRATEGY_NY_M15_SWEEP_RECLAIM"
        ),
        STRATEGY_TESTER_NYM15SR_NACUSD_RECLAIM_HOLD_PRESET: (
            "STRATEGY_NY_M15_SWEEP_RECLAIM"
        ),
        STRATEGY_TESTER_NYM15SR_NACUSD_RELAXED_M15_RECLAIM_HOLD_PRESET: (
            "STRATEGY_NY_M15_SWEEP_RECLAIM"
        ),
        STRATEGY_TESTER_NYM15SR_SPCUSD_PRESET: "STRATEGY_NY_M15_SWEEP_RECLAIM",
    }
    expected_values["strategy_selection"] = _preset_strategy_map[settings.preset_name]
    for field_name, expected in expected_values.items():
        actual = getattr(settings, field_name)
        if actual != expected:
            failures.append(f"{settings.preset_name} requires {field_name}={expected!r}")


def generate_settings_artifacts(
    *,
    output_path: str | Path,
    preset_name: str = "trial-monitor-only",
    account_program: str = "TrialRiskFree",
    stage: str = "Trial",
    approval_metadata: ApprovalMetadata | None = None,
    overrides: dict[str, Any] | None = None,
) -> GeneratedSettingsArtifacts:
    settings = build_settings(
        preset_name=preset_name,
        account_program=account_program,
        stage=stage,
        approval_metadata=approval_metadata,
        overrides=overrides,
    )
    set_path = Path(output_path)
    set_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = set_path.with_suffix(".summary.json")
    summary_md_path = set_path.with_suffix(".summary.md")
    set_path.write_text(render_set_file(settings), encoding="utf-8")
    summary = settings_summary(settings, set_path)
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(render_settings_summary_markdown(summary), encoding="utf-8")
    return GeneratedSettingsArtifacts(
        status="PASS",
        set_path=str(set_path),
        summary_json_path=str(summary_json_path),
        summary_md_path=str(summary_md_path),
        message=(
            "EA Trial Risk-Free micro-execution settings generated; "
            "protected accounts remain blocked"
            if settings.enable_trial_execution
            else (
                "EA Strategy Tester simulated execution settings generated; "
                "live/protected accounts remain blocked"
                if settings.strategy_tester_execution_mode
                else "EA settings generated; trading remains disabled"
            )
        ),
        settings=settings,
    )


def render_set_file(settings: EaSettings) -> str:
    lines = {
        "EnableTrading": _bool(settings.enable_trading),
        "EnableTrialExecution": _bool(settings.enable_trial_execution),
        "StrategyTesterExecutionMode": _bool(settings.strategy_tester_execution_mode),
        "EnablePropChallengeMode": _bool(settings.enable_prop_challenge_mode),
        "AccountProgram": ACCOUNT_PROGRAM_ENUMS[settings.account_program],
        "AccountStage": ACCOUNT_STAGE_ENUMS[settings.account_stage],
        "RequireManualConfirmationText": _bool(settings.require_manual_confirmation_text),
        "ManualConfirmationText": settings.manual_confirmation_text,
        "AccountProgramRulesReviewId": (
            settings.approval_metadata.account_program_rules_review_id
        ),
        "TrialEvidenceId": settings.approval_metadata.trial_evidence_id,
        "SourceScanPassId": settings.approval_metadata.source_scan_pass_id,
        "CompilePassId": settings.approval_metadata.compile_pass_id,
        "FinalAuditPackageId": settings.approval_metadata.final_audit_package_id,
        "HumanApprovalId": settings.approval_metadata.human_approval_id,
        "PropDayResetTimezone": settings.prop_day_reset_timezone,
        "PropDayResetTimezoneConfirmationId": (
            settings.approval_metadata.prop_day_reset_timezone_confirmation_id
        ),
        "DynamicRiskShieldConfirmationId": (
            settings.approval_metadata.dynamic_risk_shield_confirmation_id
        ),
        "MaxDailyLossSoftPct": f"{settings.max_daily_loss_soft_pct:.2f}",
        "MaxDailyLossHardPct": f"{settings.max_daily_loss_hard_pct:.2f}",
        "MaxOverallLossSoftPct": f"{settings.max_overall_loss_soft_pct:.2f}",
        "MaxOverallLossHardPct": f"{settings.max_overall_loss_hard_pct:.2f}",
        "RiskPerTradePct": f"{settings.risk_per_trade_pct:.2f}",
        "MaxRiskPerTradePct": f"{settings.max_risk_per_trade_pct:.2f}",
        "MaxTradesPerDay": str(settings.max_trades_per_day),
        "MaxServerMessagesPerDay": str(settings.max_server_messages_per_day),
        "MinHoldSeconds": str(settings.min_hold_seconds),
        "StopLossRequired": _bool(settings.stop_loss_required),
        "MaxOpenPositionsTotal": str(settings.max_open_positions_total),
        "MaxOpenPositionsPerSymbol": str(settings.max_open_positions_per_symbol),
        "AllowedSymbols": settings.allowed_symbols,
        "TrialExecutionMagicNumber": str(settings.trial_execution_magic_number),
        "AllowGrid": _bool(settings.allow_grid),
        "AllowMartingale": _bool(settings.allow_martingale),
        "AllowAveragingDown": _bool(settings.allow_averaging_down),
        "AllowHFT": _bool(settings.allow_hft),
        "AllowArbitrage": _bool(settings.allow_arbitrage),
        "AllowCopyTrading": _bool(settings.allow_copy_trading),
        "AllowScalpingUnder2Minutes": _bool(settings.allow_scalping_under_2_minutes),
        "StrategySelection": settings.strategy_selection,
        "StrategyTimeframe": settings.strategy_timeframe,
        "OpeningRangeMinutes": str(settings.opening_range_minutes),
        "OpeningRangeMinRangePoints": f"{settings.opening_range_min_range_points:.2f}",
        "OpeningRangeTakeProfitR": f"{settings.opening_range_take_profit_r:.2f}",
        "VWAPLookbackBars": str(settings.vwap_lookback_bars),
        "VWAPStopBufferPoints": f"{settings.vwap_stop_buffer_points:.2f}",
        "NYM15SRNYOpenHour": str(settings.nym15sr_ny_open_hour),
        "NYM15SRNYOpenMinute": str(settings.nym15sr_ny_open_minute),
        "NYM15SRNYWindowEndHour": str(settings.nym15sr_ny_window_end_hour),
        "NYM15SRNYWindowEndMinute": str(settings.nym15sr_ny_window_end_minute),
        "NYM15SREMAPeriod": str(settings.nym15sr_ema_period),
        "NYM15SRMinCRTRangePoints": f"{settings.nym15sr_min_crt_range_points:.2f}",
        "NYM15SRMinSweepPoints": f"{settings.nym15sr_min_sweep_points:.2f}",
        "NYM15SRStopBufferPoints": f"{settings.nym15sr_stop_buffer_points:.2f}",
        "NYM15SRTakeProfitR": f"{settings.nym15sr_take_profit_r:.2f}",
        "NYM15SRMaxBarsAfterSweep": str(settings.nym15sr_max_bars_after_sweep),
        "NYM15SRRequireM15DirectionAgreement": _bool(
            settings.nym15sr_require_m15_direction_agreement
        ),
        "NYM15SRRequireReclaimBreakoutEntry": _bool(
            settings.nym15sr_require_reclaim_breakout_entry
        ),
        "StrategySignalCooldownSeconds": str(settings.strategy_signal_cooldown_seconds),
        "MaxSignalsPerStrategyPerSession": str(settings.max_signals_per_strategy_per_session),
        "BrokerTimeMode": settings.broker_time_mode,
        "BrokerServerUtcOffsetMinutes": str(settings.broker_server_utc_offset_minutes),
        "RequireBrokerTimeValidation": _bool(settings.require_broker_time_validation),
        "BrokerTimeValidationNote": settings.broker_time_validation_note,
        "MaxSpreadPoints": str(settings.max_spread_points),
        "UseSpreadFilter": _bool(settings.use_spread_filter),
        "SpreadUnknownBlocksTrading": _bool(settings.spread_unknown_blocks_trading),
        "EvaluationMode": settings.evaluation_mode,
        "MinEvaluationSeconds": str(settings.min_evaluation_seconds),
        "LogThrottleSkips": _bool(settings.log_throttle_skips),
    }
    return "\n".join(f"{key}={value}" for key, value in lines.items()) + "\n"


def settings_summary(settings: EaSettings, set_path: Path) -> dict[str, Any]:
    protected_stage = settings.account_stage in PROTECTED_STAGES
    protected_program = settings.account_program in PROTECTED_PROGRAMS
    rule_unverified_program = settings.account_program in RULE_UNVERIFIED_PROGRAMS
    return {
        "status": "PASS",
        "preset_name": settings.preset_name,
        "set_path": str(set_path),
        "account_program": settings.account_program,
        "account_stage": settings.account_stage,
        "monitor_only": (
            not settings.enable_trial_execution
            and not settings.strategy_tester_execution_mode
        ),
        "trial_execution_enabled": settings.enable_trial_execution,
        "strategy_tester_execution_mode": settings.strategy_tester_execution_mode,
        "trial_micro_execution_preset": settings.preset_name == TRIAL_MICRO_EXECUTION_PRESET,
        "strategy_tester_preset": settings.preset_name in STRATEGY_TESTER_PRESETS,
        "trading_enabled": settings.enable_trading,
        "prop_challenge_mode": settings.enable_prop_challenge_mode,
        "python_is_execution_layer": False,
        "protected_account_programs_blocked": True,
        "surge_2_step_rule_unverified": True,
        "vanguard_blocked": True,
        "protected_stage": protected_stage,
        "protected_program": protected_program,
        "rule_unverified_program": rule_unverified_program,
        "approval_metadata_complete": (
            not settings.approval_metadata.missing_for_protected_stage()
            if protected_stage
            else False
        ),
        "settings": to_jsonable(settings),
        "source_scan_pass_id": settings.approval_metadata.source_scan_pass_id,
        "remaining_blockers": [
            "daily reset timezone confirmation",
            "Dynamic Risk Shield exact calculation",
            "Surge 2 Step exact rules review before challenge-style use",
            "Vanguard exact rules review before protected use",
            "trial evidence before protected use",
            "manual Trial Risk-Free micro-execution approval before EnableTrialExecution=true",
            "Strategy Tester simulated results before any strategy confidence claim",
            "final audit package and explicit human approval",
        ],
    }


def render_settings_summary_markdown(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# EA Settings Summary",
            "",
            f"- Status: {summary['status']}",
            f"- Preset: {summary['preset_name']}",
            f"- Account program: {summary['account_program']}",
            f"- Stage: {summary['account_stage']}",
            f"- Trading enabled: {summary['trading_enabled']}",
            f"- Trial execution enabled: {summary['trial_execution_enabled']}",
            f"- Strategy Tester execution mode: {summary['strategy_tester_execution_mode']}",
            f"- Prop challenge mode: {summary['prop_challenge_mode']}",
            "- Python execution layer: false",
            "- Protected account programs blocked: true",
            "- Surge 2 Step rule-unverified: true",
            "- Vanguard blocked: true",
            f"- Source scan PASS ID: {summary['source_scan_pass_id'] or 'missing'}",
            "",
            (
                "These settings arm Trial Risk-Free EURUSD micro-execution only. "
                "Disable EnableTrialExecution immediately after the first accepted "
                "trade or first broker rejection."
                if summary["trial_execution_enabled"]
                else (
                    "These settings arm Strategy Tester simulated execution only. "
                    "They must be used inside MT5 Strategy Tester, not on a live chart."
                    if summary["strategy_tester_execution_mode"]
                    else (
                    "These settings keep execution disabled by default for EA testing "
                    "and audit support."
                    )
                )
            ),
            "They are not approval for Surge 2 Step, Vanguard, protected stages, or live use.",
            "",
        ]
    )


def _bool(value: bool) -> str:
    return "true" if value else "false"

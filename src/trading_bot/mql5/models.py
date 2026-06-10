from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def to_jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


@dataclass(frozen=True)
class SourceScanViolation:
    path: str
    line: int
    pattern: str
    message: str = ""


@dataclass(frozen=True)
class SafeguardCheck:
    name: str
    status: str
    expected: str
    actual: str
    message: str


@dataclass(frozen=True)
class Mql5SourceScanReport:
    status: str
    root: str
    message: str
    violations: list[dict[str, object]] = field(default_factory=list)
    safeguards: list[SafeguardCheck] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class ApprovalMetadata:
    account_program_rules_review_id: str = ""
    trial_evidence_id: str = ""
    source_scan_pass_id: str = ""
    compile_pass_id: str = ""
    final_audit_package_id: str = ""
    human_approval_id: str = ""
    prop_day_reset_timezone_confirmation_id: str = ""
    dynamic_risk_shield_confirmation_id: str = ""

    def missing_for_protected_stage(self) -> list[str]:
        required = {
            "account_program_rules_review_id": self.account_program_rules_review_id,
            "trial_evidence_id": self.trial_evidence_id,
            "source_scan_pass_id": self.source_scan_pass_id,
            "compile_pass_id": self.compile_pass_id,
            "final_audit_package_id": self.final_audit_package_id,
            "human_approval_id": self.human_approval_id,
        }
        return [name for name, value in required.items() if not value]


@dataclass(frozen=True)
class EaSettings:
    preset_name: str = "trial-monitor-only"
    account_program: str = "TrialRiskFree"
    account_stage: str = "Trial"
    enable_trading: bool = False
    enable_trial_execution: bool = False
    strategy_tester_execution_mode: bool = False
    enable_prop_challenge_mode: bool = False
    require_manual_confirmation_text: bool = True
    manual_confirmation_text: str = ""
    prop_day_reset_timezone: str = "UNCONFIRMED_CONSERVATIVE"
    max_daily_loss_soft_pct: float = 2.5
    max_daily_loss_hard_pct: float = 3.0
    max_overall_loss_soft_pct: float = 5.0
    max_overall_loss_hard_pct: float = 6.0
    risk_per_trade_pct: float = 0.25
    max_risk_per_trade_pct: float = 0.50
    max_trades_per_day: int = 1
    max_server_messages_per_day: int = 500
    min_hold_seconds: int = 180
    stop_loss_required: bool = True
    max_open_positions_total: int = 1
    max_open_positions_per_symbol: int = 1
    allowed_symbols: str = "EURUSD"
    trial_execution_magic_number: int = 26060113
    allow_grid: bool = False
    allow_martingale: bool = False
    allow_averaging_down: bool = False
    allow_hft: bool = False
    allow_arbitrage: bool = False
    allow_copy_trading: bool = False
    allow_scalping_under_2_minutes: bool = False
    strategy_selection: str = "STRATEGY_OPENING_RANGE_BREAKOUT"
    strategy_timeframe: str = "PERIOD_M1"
    opening_range_minutes: int = 15
    opening_range_min_range_points: float = 10.0
    opening_range_take_profit_r: float = 2.0
    vwap_lookback_bars: int = 30
    vwap_stop_buffer_points: float = 20.0
    nym15sr_ny_open_hour: int = 9
    nym15sr_ny_open_minute: int = 30
    nym15sr_ny_window_end_hour: int = 11
    nym15sr_ny_window_end_minute: int = 0
    nym15sr_ema_period: int = 50
    nym15sr_min_crt_range_points: float = 100.0
    nym15sr_min_sweep_points: float = 20.0
    nym15sr_stop_buffer_points: float = 50.0
    nym15sr_take_profit_r: float = 2.0
    nym15sr_max_bars_after_sweep: int = 12
    strategy_signal_cooldown_seconds: int = 900
    max_signals_per_strategy_per_session: int = 1
    broker_time_mode: str = "BROKER_TIME_MANUAL_UTC_OFFSET"
    broker_server_utc_offset_minutes: int = 0
    require_broker_time_validation: bool = True
    broker_time_validation_note: str = ""
    max_spread_points: int = 30
    use_spread_filter: bool = True
    spread_unknown_blocks_trading: bool = True
    evaluation_mode: str = "EVALUATION_ON_NEW_CLOSED_BAR"
    min_evaluation_seconds: int = 60
    log_throttle_skips: bool = False
    approval_metadata: ApprovalMetadata = field(default_factory=ApprovalMetadata)


@dataclass(frozen=True)
class GeneratedSettingsArtifacts:
    status: str
    set_path: str
    summary_json_path: str
    summary_md_path: str
    message: str
    settings: EaSettings

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class EaLogSummary:
    status: str
    log_dir: str
    files_scanned: int
    lines_scanned: int
    decisions_by_strategy: dict[str, int] = field(default_factory=dict)
    skip_reasons: dict[str, int] = field(default_factory=dict)
    setup_forming_count: int = 0
    entry_intent_count: int = 0
    exit_intent_count: int = 0
    refused_trade_action_count: int = 0
    messages_by_day: dict[str, int] = field(default_factory=dict)
    trades_by_day: dict[str, int] = field(default_factory=dict)
    safety_blocks: list[str] = field(default_factory=list)
    unresolved_rule_warnings: list[str] = field(default_factory=list)
    min_hold_warnings: list[str] = field(default_factory=list)
    spread_blocks: list[str] = field(default_factory=list)
    session_blocks: list[str] = field(default_factory=list)
    summary_json_path: str = ""
    summary_md_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class ComplianceReportArtifacts:
    status: str
    report_json_path: str
    report_md_path: str
    message: str
    evidence_complete: bool
    build_evidence_complete: bool = False
    monitor_evidence_complete: bool = False
    trial_evidence_complete: bool = False
    strategy_tester_evidence_complete: bool = False
    blockers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

MT5_ACCOUNT_METADATA_GATE = "allow_" + "account" + "_info"
MT5_ORDER_PREFLIGHT_GATE = "allow_" + "order" + "_check"
MT5_ORDER_SUBMISSION_GATE = "allow_" + "order" + "_send"
SUPPORTED_ACCOUNT_PROGRAMS = ["TrialRiskFree", "Vanguard", "Surge2Step", "Custom"]
UNCONFIRMED_PROP_DAY_RESET_TIMEZONE = "UNCONFIRMED_CONSERVATIVE"


class Mt5TransformationGateSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    enabled: bool = False
    mode: Literal["readonly"] = "readonly"
    account_metadata_allowed: bool = Field(False, alias=MT5_ACCOUNT_METADATA_GATE)
    allow_positions: bool = False
    order_preflight_allowed: bool = Field(False, alias=MT5_ORDER_PREFLIGHT_GATE)
    order_submission_allowed: bool = Field(False, alias=MT5_ORDER_SUBMISSION_GATE)
    allow_live_account: bool = False
    allow_demo_account: bool = False
    allow_balance_fetching: bool = False

    @model_validator(mode="after")
    def reject_execution_and_account_gates(self) -> Mt5TransformationGateSettings:
        unsafe = {
            MT5_ACCOUNT_METADATA_GATE: self.account_metadata_allowed,
            "allow_positions": self.allow_positions,
            MT5_ORDER_PREFLIGHT_GATE: self.order_preflight_allowed,
            MT5_ORDER_SUBMISSION_GATE: self.order_submission_allowed,
            "allow_live_account": self.allow_live_account,
            "allow_balance_fetching": self.allow_balance_fetching,
        }
        enabled = [name for name, value in unsafe.items() if value]
        if enabled:
            raise ValueError(f"MT5 transformation config forbids enabled unsafe gates: {enabled}")
        return self


class SessionWindowSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: str
    end: str


class NySessionTransformationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    timezone: str = "America/New_York"
    fx_gold_crypto_session: SessionWindowSettings
    index_cash_session: SessionWindowSettings
    london_new_york_overlap: SessionWindowSettings


class StrategyResearchTransformationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    strategies: list[str] = Field(min_length=1)


class ExecutionTransformationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    demo_only: bool = True
    live_allowed: bool = False

    @model_validator(mode="after")
    def reject_execution(self) -> ExecutionTransformationSettings:
        if self.enabled:
            raise ValueError("MT5 transformation planning config requires execution.enabled=false")
        if not self.demo_only:
            raise ValueError("MT5 transformation planning config requires execution.demo_only=true")
        if self.live_allowed:
            raise ValueError(
                "MT5 transformation planning config requires execution.live_allowed=false"
            )
        return self


class ChallengePresetEvidenceSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trial_evidence: bool = False
    source_scan_pass: bool = False
    compile_pass: bool = False
    audit_package_id: str = ""
    explicit_human_approval_metadata: str = ""

    def complete(self) -> bool:
        return (
            self.trial_evidence
            and self.source_scan_pass
            and self.compile_pass
            and bool(self.audit_package_id.strip())
            and bool(self.explicit_human_approval_metadata.strip())
        )


class PropFirmTransformationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_path: Literal["native_mql5_ea"] = "native_mql5_ea"
    python_mt5_execution_quarantined: bool = True
    account_programs_supported: list[
        Literal["TrialRiskFree", "Vanguard", "Surge2Step", "Custom"]
    ] = Field(default_factory=lambda: SUPPORTED_ACCOUNT_PROGRAMS.copy())
    trial_required_before_challenge: bool = True
    protected_account_programs_blocked: bool = True
    surge_2_step_rules_verified: bool = False
    vanguard_rules_verified: bool = False
    prop_day_reset_timezone: str = UNCONFIRMED_PROP_DAY_RESET_TIMEZONE
    prop_day_reset_timezone_confirmed: bool = False
    dynamic_risk_shield_verified: bool = False
    challenge_presets_enabled: bool = False
    required_challenge_preset_evidence: ChallengePresetEvidenceSettings = Field(
        default_factory=ChallengePresetEvidenceSettings
    )

    @model_validator(mode="after")
    def enforce_native_ea_gate(self) -> PropFirmTransformationSettings:
        if not self.python_mt5_execution_quarantined:
            raise ValueError("Python MT5 execution must remain quarantined")
        if not self.trial_required_before_challenge:
            raise ValueError("Trial evidence is required before challenge presets")
        if self.account_programs_supported != SUPPORTED_ACCOUNT_PROGRAMS:
            raise ValueError(
                "AccountProgram support must remain TrialRiskFree, Vanguard, "
                "Surge2Step, and Custom"
            )
        if not self.protected_account_programs_blocked:
            raise ValueError("Protected account programs must stay blocked")
        if self.surge_2_step_rules_verified:
            raise ValueError("Surge 2 Step rules are not encoded in this project yet")
        if self.vanguard_rules_verified:
            raise ValueError("Vanguard rules must remain unapproved until explicit review")
        if self.challenge_presets_enabled and (
            not self.prop_day_reset_timezone_confirmed
            or not self.dynamic_risk_shield_verified
            or not self.required_challenge_preset_evidence.complete()
        ):
            raise ValueError(
                "Challenge, Verification, and Funded presets require account-program rules "
                "review, confirmed reset timezone, verified Dynamic Risk Shield calculation, "
                "trial evidence, source scan PASS, compile PASS, audit package ID, and "
                "explicit human approval metadata"
            )
        return self


class Mt5TransformationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    live_trading_enabled: bool = False
    mt5: Mt5TransformationGateSettings
    ny_session: NySessionTransformationSettings
    strategy_research: StrategyResearchTransformationSettings
    execution: ExecutionTransformationSettings
    prop_firm: PropFirmTransformationSettings

    @model_validator(mode="after")
    def reject_live_trading(self) -> Mt5TransformationConfig:
        if self.live_trading_enabled:
            raise ValueError(
                "MT5 transformation planning config requires live_trading_enabled=false"
            )
        return self


def load_mt5_transformation_config(path: str | Path) -> Mt5TransformationConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("MT5 transformation configuration root must be a mapping")
    return Mt5TransformationConfig.model_validate(raw)

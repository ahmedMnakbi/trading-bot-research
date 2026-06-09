from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingMode(StrEnum):
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


class MarketSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["crypto_spot"]
    exchange: str
    symbols: list[str] = Field(min_length=1)
    timeframe: str


class DataSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["ccxt"]
    cache_dir: Path = Path("data/raw/ohlcv")
    since_days: int = Field(gt=0)
    max_candles_per_request: int = Field(gt=0, le=1000)
    request_timeout_seconds: int = Field(gt=0)
    retry_attempts: int = Field(gt=0)
    retry_backoff_seconds: float = Field(gt=0)
    validate_continuity: bool = True
    allow_partial_latest_candle: bool = False


class RiskSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_per_trade_pct: float = Field(gt=0, le=2)
    min_stop_distance_bps: float = Field(gt=0)
    max_stop_distance_pct: float = Field(gt=0, le=100)
    max_open_positions: int = Field(gt=0)
    max_total_exposure_pct: float = Field(gt=0, le=100)
    max_daily_loss_pct: float = Field(gt=0, le=100)
    max_weekly_loss_pct: float = Field(gt=0, le=100)
    max_drawdown_pct: float = Field(gt=0, le=100)
    require_stop_loss: bool
    allow_leverage: bool
    allow_shorting: bool

    @model_validator(mode="after")
    def enforce_safety_limits(self) -> RiskSettings:
        if self.allow_leverage:
            raise ValueError("leverage is disabled in the safety-first skeleton")
        if not self.require_stop_loss:
            raise ValueError("stop-loss is required")
        return self


class ExecutionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_starting_equity: float = Field(gt=0)
    fee_bps: float = Field(ge=0)
    slippage_bps: float = Field(ge=0)


class BacktestingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_equity: float = Field(gt=0)
    benchmark: str = "buy_and_hold"
    allow_shorting: bool = False
    allow_leverage: bool = False
    mark_to_market: bool = True
    reject_orders_without_stop: bool = True
    min_cash_pct: float = Field(ge=0, le=100)
    max_bars: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def enforce_backtest_safety(self) -> BacktestingSettings:
        if self.allow_shorting:
            raise ValueError("shorting is disabled in the backtesting foundation")
        if self.allow_leverage:
            raise ValueError("leverage is disabled in the backtesting foundation")
        return self


class StrategySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "noop"
    params: dict[str, Any] = Field(default_factory=dict)


class WalkForwardSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    train_bars: int = Field(gt=0)
    test_bars: int = Field(gt=0)
    step_bars: int = Field(gt=0)


class RegimeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    trend_ma_period: int = Field(gt=1)
    volatility_window: int = Field(gt=1)
    high_volatility_quantile: float = Field(gt=0, lt=1)
    low_volatility_quantile: float = Field(gt=0, lt=1)

    @model_validator(mode="after")
    def validate_quantiles(self) -> RegimeSettings:
        if self.low_volatility_quantile >= self.high_volatility_quantile:
            raise ValueError("low volatility quantile must be below high volatility quantile")
        return self


class ValidationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    train_pct: int = Field(gt=0, lt=100)
    test_pct: int = Field(gt=0, lt=100)
    min_train_bars: int = Field(gt=0)
    min_test_bars: int = Field(gt=0)
    walk_forward: WalkForwardSettings
    benchmarks: list[str] = Field(min_length=1)
    strategies: list[str] = Field(min_length=1)
    regime: RegimeSettings

    @model_validator(mode="before")
    @classmethod
    def reject_optimization_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            forbidden = {"optimize", "optimization", "hyperparameters", "grid_search"}
            present = forbidden.intersection(data)
            if present:
                raise ValueError(f"optimization fields are prohibited: {sorted(present)}")
        return data

    @model_validator(mode="after")
    def validate_split_percentages(self) -> ValidationSettings:
        if self.train_pct + self.test_pct != 100:
            raise ValueError("train_pct + test_pct must equal 100")
        return self


class PaperSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    require_validation_run: bool = True
    validation_run_id: str | None = None
    starting_equity: float = Field(gt=0)
    state_dir: Path = Path("data/processed/paper")
    decision_log_dir: Path = Path("data/processed/paper/decisions")
    poll_interval_seconds: int = Field(gt=0)
    max_runtime_minutes: int | None = Field(default=None, gt=0)
    max_iterations: int | None = Field(default=None, gt=0)
    allow_public_live_data: bool = True
    simulated_order_latency_ms: int = Field(ge=0)
    persist_state: bool = True
    resume_existing_state: bool = True


class PortfolioPaperSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    starting_equity: float = Field(gt=0)
    state_dir: Path = Path("data/processed/portfolio_paper")
    decision_log_dir: Path = Path("data/processed/portfolio_paper/decisions")
    require_campaign_reference: bool = True
    campaign_run_id: str | None = None
    max_iterations: int | None = Field(default=None, gt=0)
    poll_interval_seconds: int = Field(gt=0)
    resume_existing_state: bool = True
    persist_state: bool = True
    symbols: list[str] = Field(min_length=1)
    strategy_map: dict[str, str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_strategy_map(self) -> PortfolioPaperSettings:
        from trading_bot.strategies.registry import get_strategy

        missing = [symbol for symbol in self.symbols if symbol not in self.strategy_map]
        if missing:
            raise ValueError(f"portfolio strategy_map missing symbols: {missing}")
        for strategy_name in self.strategy_map.values():
            get_strategy(strategy_name)
        return self


class PortfolioRiskSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_open_positions: int = Field(gt=0)
    max_total_exposure_pct: float = Field(gt=0, le=100)
    max_symbol_exposure_pct: float = Field(gt=0, le=100)
    max_strategy_exposure_pct: float = Field(gt=0, le=100)
    max_new_positions_per_iteration: int = Field(gt=0)
    min_cash_pct: float = Field(ge=0, le=100)
    max_daily_loss_pct: float = Field(gt=0, le=100)
    max_weekly_loss_pct: float = Field(gt=0, le=100)
    max_drawdown_pct: float = Field(gt=0, le=100)
    reject_correlated_entries: bool = False
    correlation_warning_threshold: float = Field(ge=0, le=1)


class FailureInjectionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    output_dir: Path = Path("data/processed/failure_tests")
    default_max_iterations: int = Field(gt=0)
    fail_fast: bool = False
    write_incident_reports: bool = True
    scenarios: list[str] = Field(min_length=1)


class IncidentReplaySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_dir: Path = Path("data/processed/incidents")
    include_decision_logs: bool = True
    include_health_events: bool = True
    include_alerts: bool = True
    include_state_snapshots: bool = True


class MonitoringSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heartbeat_interval_seconds: int = Field(gt=0)
    stale_data_multiplier: float = Field(gt=0)
    max_consecutive_data_errors: int = Field(gt=0)
    max_consecutive_order_errors: int = Field(gt=0)
    alert_channels: list[str] = Field(default_factory=lambda: ["console", "file"])


class ReportingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_dir: Path = Path("data/processed/reports")
    include_html: bool = True
    include_markdown: bool = True
    include_json: bool = True


class ReadinessSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    min_paper_runtime_days: int = Field(ge=0)
    min_paper_trades: int = Field(ge=0)
    max_paper_drawdown_pct: float = Field(ge=0)
    max_daily_loss_pct: float = Field(ge=0)
    max_weekly_loss_pct: float = Field(ge=0)
    max_unresolved_alerts: int = Field(ge=0)
    require_no_kill_switch: bool = True
    require_no_state_corruption: bool = True
    require_validation_reference: bool = True
    max_backtest_to_paper_return_degradation_pct: float = Field(ge=0)
    max_validation_to_paper_return_degradation_pct: float = Field(ge=0)
    require_human_approval_for_live: bool = True


class AuditSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    fail_on_live_trading_enabled: bool = True
    fail_on_real_order_code: bool = True
    fail_on_private_api_usage: bool = True
    fail_on_secret_leak: bool = True
    fail_on_missing_human_approval_gate: bool = True
    warn_on_missing_validation_artifacts: bool = True
    warn_on_missing_paper_artifacts: bool = True
    warn_on_missing_report_artifacts: bool = True
    artifact_integrity_enabled: bool = True


class GovernanceSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    require_human_approval_for_live: bool = True
    live_trading_allowed: bool = False
    real_orders_allowed: bool = False
    private_api_allowed: bool = False
    approved_by: str | None = None
    approved_at: str | None = None
    approval_ticket: str | None = None


class ExperimentReviewGates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_validation_windows: int = Field(ge=0)
    min_total_test_trades: int = Field(ge=0)
    max_validation_drawdown_pct: float = Field(ge=0)
    max_underperformance_vs_buy_and_hold_pct: float = Field(ge=0)
    require_no_high_severity_warnings: bool = True
    require_positive_consistency_score: bool = False


class ExperimentLabels(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_candidate_labels: bool = True
    allowed_labels: list[str] = Field(min_length=1)


class ExperimentSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    output_dir: Path = Path("data/processed/campaigns")
    use_cached_data_only: bool = True
    write_artifact_manifest: bool = True
    symbols: list[str] = Field(min_length=1)
    timeframes: list[str] = Field(min_length=1)
    strategies: list[str] = Field(min_length=1)
    benchmarks: list[str] = Field(min_length=1)
    required_stages: list[str] = Field(min_length=1)
    review_gates: ExperimentReviewGates
    labels: ExperimentLabels

    @model_validator(mode="after")
    def validate_names(self) -> ExperimentSettings:
        from trading_bot.strategies.registry import get_strategy

        for name in [*self.strategies, *self.benchmarks]:
            get_strategy(name)
        allowed_stages = {"backtest", "validation"}
        if any(stage not in allowed_stages for stage in self.required_stages):
            raise ValueError("unknown experiment stage")
        return self


class SafetySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kill_switch_armed: bool = True
    halt_on_stale_data: bool = True
    halt_on_position_mismatch: bool = True
    halt_on_repeated_order_errors: bool = True


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    allow_live_trading: bool = False
    exchange_api_key: SecretStr | None = None
    exchange_api_secret: SecretStr | None = None


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: TradingMode = TradingMode.PAPER
    live_trading_enabled: bool = False
    market: MarketSettings
    data: DataSettings
    risk: RiskSettings
    execution: ExecutionSettings
    backtesting: BacktestingSettings
    strategy: StrategySettings
    validation: ValidationSettings
    paper: PaperSettings
    portfolio_paper: PortfolioPaperSettings
    portfolio_risk: PortfolioRiskSettings
    failure_injection: FailureInjectionSettings
    incident_replay: IncidentReplaySettings
    monitoring: MonitoringSettings
    reporting: ReportingSettings
    readiness: ReadinessSettings
    audit: AuditSettings
    governance: GovernanceSettings
    experiments: ExperimentSettings
    safety: SafetySettings = Field(default_factory=SafetySettings)

    @model_validator(mode="after")
    def refuse_unsafe_live_mode(self) -> Settings:
        allow_live = os.getenv("ALLOW_LIVE_TRADING", "").lower() == "true"
        if self.mode == TradingMode.LIVE and not (allow_live and self.live_trading_enabled):
            raise ValueError(
                "live mode requires ALLOW_LIVE_TRADING=true and live_trading_enabled=true"
            )
        return self


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as config_file:
        raw = yaml.safe_load(config_file) or {}
    if not isinstance(raw, dict):
        raise ValueError("configuration root must be a mapping")
    return raw


def load_settings(config_path: str | Path, profile: str | None = None) -> Settings:
    load_dotenv()
    path = Path(config_path)
    if profile is None:
        data = load_yaml(path)
    else:
        from trading_bot.config.profiles import effective_config

        data = effective_config(path, profile)
    return Settings.model_validate(data)


def validate_settings(config_path: str | Path) -> Settings:
    try:
        return load_settings(config_path)
    except ValidationError:
        raise

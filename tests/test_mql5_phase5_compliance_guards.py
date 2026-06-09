from __future__ import annotations

from pathlib import Path

from scripts.compile_mql5_ea import compile_ea
from scripts.run_mql5_source_scan import run_mql5_source_scan

ROOT = Path(__file__).resolve().parents[1]
MQL5_ROOT = ROOT / "mql5"
EA_SOURCE = (
    MQL5_ROOT
    / "Experts"
    / "UpcomersNYSessionPropBot"
    / "UpcomersNYSessionPropBot.mq5"
)
INCLUDE_ROOT = MQL5_ROOT / "Include" / "UpcomersNYSessionPropBot"
CONFIG_TEXT = (INCLUDE_ROOT / "Config.mqh").read_text(encoding="utf-8")
PROP_RULES_TEXT = (INCLUDE_ROOT / "PropFirmRules.mqh").read_text(encoding="utf-8")
RISK_TEXT = (INCLUDE_ROOT / "RiskManager.mqh").read_text(encoding="utf-8")
MESSAGE_COUNTER_TEXT = (INCLUDE_ROOT / "MessageCounter.mqh").read_text(encoding="utf-8")
STATE_TEXT = (INCLUDE_ROOT / "StateManager.mqh").read_text(encoding="utf-8")
TRADE_MANAGER_TEXT = (INCLUDE_ROOT / "TradeManager.mqh").read_text(encoding="utf-8")
AUDIT_TEXT = (INCLUDE_ROOT / "AuditLogger.mqh").read_text(encoding="utf-8")


def _all_mql5_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in MQL5_ROOT.rglob("*.mq*"))


def test_phase5_config_validation_rejects_unsafe_settings() -> None:
    required_branches = [
        "ValidatePhase5ComplianceConfig",
        "config.EnableTrading &&",
        "ManualConfirmationText != UPCOMERS_REQUIRED_CONFIRMATION_TEXT",
        "config.EnablePropChallengeMode",
        "IsRuleUnverifiedAccountProgram(config.AccountProgram)",
        "IsProtectedAccountStage(config.AccountStage)",
        "config.MaxDailyLossHardPct >= 4.0",
        "config.MaxOverallLossHardPct >= 7.0",
        "config.MaxDailyLossSoftPct >= config.MaxDailyLossHardPct",
        "config.MaxOverallLossSoftPct >= config.MaxOverallLossHardPct",
        "config.RiskPerTradePct > config.MaxRiskPerTradePct",
        "config.MaxRiskPerTradePct > 0.50",
        "config.MinHoldSeconds < 180",
        "!config.StopLossRequired",
        "config.MaxTradesPerDay <= 0 || config.MaxTradesPerDay > 20",
        "config.MaxServerMessagesPerDay <= 0 || config.MaxServerMessagesPerDay > 2000",
        "config.AllowGrid || config.AllowMartingale || config.AllowAveragingDown",
        "config.AllowHFT || config.AllowArbitrage || config.AllowCopyTrading",
        "config.AllowScalpingUnder2Minutes",
    ]

    for snippet in required_branches:
        assert snippet in CONFIG_TEXT


def test_protected_stages_require_all_approval_metadata() -> None:
    required_metadata = [
        "TrialEvidenceId",
        "AccountProgramRulesReviewId",
        "SourceScanPassId",
        "CompilePassId",
        "FinalAuditPackageId",
        "HumanApprovalId",
        "PropDayResetTimezoneConfirmationId",
        "DynamicRiskShieldConfirmationId",
        "HasRequiredProtectedStageMetadata",
    ]

    for snippet in required_metadata:
        assert snippet in CONFIG_TEXT


def test_trial_stage_is_not_vanguard_or_funded_approval() -> None:
    combined = _all_mql5_text()

    assert (
        "Trial Risk-Free testing is not approval for Surge 2 Step, Vanguard, or funded trading"
    ) in combined
    assert "Surge 2 Step is rule-unverified" in combined
    assert "Vanguard" in combined
    assert "Funded" in combined


def test_loss_guards_include_statuses_and_unresolved_rule_blocks() -> None:
    required_markers = [
        "GUARD_STATUS_OK",
        "GUARD_STATUS_SOFT_STOP",
        "GUARD_STATUS_HARD_STOP",
        "GUARD_STATUS_UNKNOWN_RULE_BLOCK",
        "PropDayResetTimezone",
        "current Upcomers reset timezone is unconfirmed",
        "Dynamic Risk Shield calculation must be verified",
        "CheckDailyLossGuard",
        "CheckOverallLossGuard",
    ]

    combined = CONFIG_TEXT + PROP_RULES_TEXT + AUDIT_TEXT
    for snippet in required_markers:
        assert snippet in combined


def test_risk_guard_requires_stop_loss_limits_positions_and_min_hold() -> None:
    required_markers = [
        "SHypotheticalTradeIntent",
        "CheckHypotheticalTradeIntent",
        "config.StopLossRequired && !intent.HasStopLoss",
        "intent.EstimatedRiskPct > config.MaxRiskPerTradePct",
        "intent.EstimatedRiskPct > 0.50",
        "config.MaxDailyLossHardPct >= 4.0",
        "config.MaxOverallLossHardPct >= 7.0",
        "config.MinHoldSeconds < 180",
        "intent.CurrentOpenPositionsTotal >= config.MaxOpenPositionsTotal",
        "intent.CurrentOpenPositionsForSymbol >= config.MaxOpenPositionsPerSymbol",
    ]

    for snippet in required_markers:
        assert snippet in RISK_TEXT


def test_min_hold_state_stub_allows_only_emergency_override() -> None:
    required_markers = [
        "SetFutureOpenTimeStub",
        "CanCloseAfterMinHold",
        "emergencyHardStopRiskReduction",
        "MinHoldSeconds guard blocks close",
    ]

    for snippet in required_markers:
        assert snippet in STATE_TEXT


def test_trade_and_message_counters_are_used_by_trade_manager() -> None:
    for snippet in [
        "CountMonitorEvaluation",
        "RecordTradeIntentEvent",
        "RecordRefusedTradeAction",
        "RecordActualServerMessage",
        "RecordTradeActionRequest",
        "RecordServerMessageRequest",
        "CheckTradeActionLimit",
        "CanSendServerMessage",
        "ResetForNewPropDay",
    ]:
        assert snippet in MESSAGE_COUNTER_TEXT
        assert snippet in _all_mql5_text()

    assert "messageCounter.RecordTradeIntentEvent()" in TRADE_MANAGER_TEXT
    assert "messageCounter.RecordRefusedTradeAction()" in TRADE_MANAGER_TEXT
    assert "messageCounter.RecordServerMessageRequest()" not in TRADE_MANAGER_TEXT
    assert "WAIT/skip/setup evaluations do not count as trade attempts or server messages" in (
        TRADE_MANAGER_TEXT
    )


def test_trade_manager_remains_refusal_only() -> None:
    assert "RefuseExecution" in TRADE_MANAGER_TEXT
    assert "TRADE_REQUEST_REJECTED" in TRADE_MANAGER_TEXT
    assert "TRADE_REQUEST_REFUSED" in TRADE_MANAGER_TEXT
    assert "REJECTED by no-trade TradeManager" in TRADE_MANAGER_TEXT
    assert "REFUSED Phase 9 no-trade TradeManager" in TRADE_MANAGER_TEXT
    assert "return false" in TRADE_MANAGER_TEXT


def test_no_order_placement_calls_exist_after_phase5() -> None:
    allowed = {
        INCLUDE_ROOT / "TrialExecution.mqh",
        INCLUDE_ROOT / "TesterExecution.mqh",
    }
    for path in MQL5_ROOT.rglob("*"):
        if path.suffix.lower() not in {".mq5", ".mqh"} or path in allowed:
            continue
        text = path.read_text(encoding="utf-8").lower()
        for pattern in [
            "ordersend(",
            "ctrade",
            ".buy(",
            ".sell(",
            "positionopen(",
            "buylimit(",
            "selllimit(",
            "buystop(",
            "sellstop(",
        ]:
            assert pattern not in text

    trial_execution_text = (INCLUDE_ROOT / "TrialExecution.mqh").read_text(encoding="utf-8")
    tester_execution_text = (INCLUDE_ROOT / "TesterExecution.mqh").read_text(encoding="utf-8")
    assert "OrderSend(request, result)" in trial_execution_text
    assert "ValidateTrialExecutionConfig" in trial_execution_text
    assert "OrderSend(request, result)" in tester_execution_text
    assert "ValidateStrategyTesterExecutionConfig" in tester_execution_text


def test_phase5_audit_logging_mentions_validation_and_blocks() -> None:
    required_markers = [
        "startup validation PASS",
        "startup validation FAIL",
        "TODO: confirm current Upcomers daily loss reset timezone",
        "TODO: verify exact Dynamic Risk Shield calculation",
        "Protected account programs remain blocked",
    ]

    for snippet in required_markers:
        assert snippet in AUDIT_TEXT


def test_mql5_source_scan_passes_phase5_source() -> None:
    result = run_mql5_source_scan(ROOT)

    assert result.status == "PASS"
    assert result.violations == []


def test_compile_wrapper_can_compile_or_skip_gracefully() -> None:
    result = compile_ea(ROOT)

    assert result.status in {"PASS", "SKIPPED"}
    assert result.log_path
    assert EA_SOURCE.exists()

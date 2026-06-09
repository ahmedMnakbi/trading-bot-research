# EA Settings Reference

This reference describes the Phase 13 settings. Execution remains disabled by default; the only active path is a tightly gated native MQL5 Trial Risk-Free micro-execution mode.

## Mode And Stage

- `EnableTrading=false`: default disabled.
- `EnableTrialExecution=false`: default disabled. Trial execution also requires `EnableTrading=true`.
- `EnablePropChallengeMode=false`: protected mode remains blocked without required approval metadata.
- `AccountProgram=ACCOUNT_PROGRAM_TRIAL_RISK_FREE`: supported programs are `TrialRiskFree`, `Vanguard`, `Surge2Step`, and `Custom`.
- `AccountStage=ACCOUNT_STAGE_MONITOR_ONLY`: supported stages are `MonitorOnly`, `Trial`, `Challenge`, `Verification`, and `Funded`.
- `RequireManualConfirmationText=true`: required before monitor-trading toggle or Trial execution.
- `ManualConfirmationText=""`: must equal `I_ACCEPT_TRIAL_RISK_FREE_EXECUTION_ONLY` for Trial micro-execution. The older monitor-only phrase `I ACCEPT MONITOR ONLY PHASE 5 - NO TRADING` does not enable Trial execution.

## Approval Metadata

Protected stages and prop challenge mode require non-empty IDs for:

- `TrialEvidenceId`
- `SourceScanPassId`
- `CompilePassId`
- `FinalAuditPackageId`
- `HumanApprovalId`
- `PropDayResetTimezoneConfirmationId`
- `DynamicRiskShieldConfirmationId`

Trial evidence is not Surge 2 Step approval, Vanguard approval, or funded approval. Surge 2 Step is rule-unverified until its exact rules are reviewed and encoded. Vanguard remains blocked until exact rules, trial evidence, audit package, and human approval metadata exist.

## Loss And Risk Controls

- `PropDayResetTimezone=UNCONFIRMED_CONSERVATIVE`: configurable placeholder until current Upcomers reset timezone is confirmed.
- `MaxDailyLossSoftPct=2.5`
- `MaxDailyLossHardPct=3.0`: rejected if `>= 4.0`.
- `MaxOverallLossSoftPct=5.0`
- `MaxOverallLossHardPct=6.0`: rejected if `>= 7.0`.
- `RiskPerTradePct=0.25`
- `MaxRiskPerTradePct=0.50`: rejected above `0.50`.
- `StopLossRequired=true`
- `MaxOpenPositionsTotal=1`
- `MaxOpenPositionsPerSymbol=1`
- `AllowedSymbols=EURUSD`
- `TrialExecutionMagicNumber=26060113`

Soft loss limits must be lower than hard loss limits. `RiskPerTradePct` must not exceed `MaxRiskPerTradePct`.

## Counters And Hold Guard

- `MaxTradesPerDay=1`: Trial micro-execution requires exactly `1`.
- `MaxServerMessagesPerDay=500`: rejected above `2000`.
- `MinHoldSeconds=180`: rejected below `180`.

`TradeManager` counts attempted trade-action and server-message requests, then refuses execution for monitor-only and all non-TrialRiskFree modes. `TrialExecution` counts a single validated Trial Risk-Free order attempt as both a trade intent and one server message.

## Prohibited Behavior Flags

These must remain false:

- `AllowGrid=false`
- `AllowMartingale=false`
- `AllowAveragingDown=false`
- `AllowHFT=false`
- `AllowArbitrage=false`
- `AllowCopyTrading=false`
- `AllowScalpingUnder2Minutes=false`

Phase 14 contains no protected account trading, prop credentials, MT5 login, Python-controlled MT5 prop execution, pending orders, scaling, retries, trailing stop, breakeven modification, or challenge approval. Live Trial micro-execution remains isolated in `TrialExecution.mqh`; Strategy Tester simulated execution is separately isolated in `TesterExecution.mqh` and can activate only inside MT5 Strategy Tester.

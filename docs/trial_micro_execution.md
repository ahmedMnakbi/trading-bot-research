# Trial Risk-Free Micro-Execution

Phase 13 adds one native MQL5 execution path for observing real order mechanics on the free Trial Risk-Free account only. It is not prop challenge approval, Surge 2 Step approval, Vanguard approval, funded approval, or live-money approval.

## Defaults

Execution remains disabled by default:

- `EnableTrading=false`
- `EnableTrialExecution=false`
- `EnablePropChallengeMode=false`
- `AccountProgram=TrialRiskFree`
- `AccountStage=MonitorOnly`
- `AllowedSymbols=EURUSD`
- `MaxTradesPerDay=1`
- `MaxOpenPositionsTotal=1`
- `MaxOpenPositionsPerSymbol=1`
- `RiskPerTradePct=0.25`
- `MaxRiskPerTradePct=0.50`
- `MinHoldSeconds=180`
- `StopLossRequired=true`
- `UseSpreadFilter=true`

## Required Gates

Trial execution can be armed only when all of these are true:

- `AccountProgram=TrialRiskFree`
- `AccountStage=Trial`
- `EnableTrading=true`
- `EnableTrialExecution=true`
- `EnablePropChallengeMode=false`
- `ManualConfirmationText=I_ACCEPT_TRIAL_RISK_FREE_EXECUTION_ONLY`
- `SourceScanPassId` is non-empty
- `AllowedSymbols=EURUSD`
- current chart symbol is `EURUSD`
- current spread is known and `<= MaxSpreadPoints`
- `MaxTradesPerDay=1`
- `MaxOpenPositionsTotal=1`
- `MaxOpenPositionsPerSymbol=1`
- `MaxServerMessagesPerDay<=500`
- strategy signal is `ENTER_LONG_INTENT` or `ENTER_SHORT_INTENT`
- strategy signal includes valid stop-loss and take-profit

Surge 2 Step, Vanguard, Challenge, Verification, Funded, and live-money trading remain blocked.

## Order Constraints

The isolated `TrialExecution.mqh` module sends at most one market request per validated signal. It attaches SL/TP immediately, uses the broker minimum lot only when that lot is within the configured risk budget, does not place pending orders, does not scale in, does not average into losing positions, does not retry rejected orders, and does not close before `MinHoldSeconds` except for future emergency hard-stop/risk-reduction logic.

If the broker rejects the request, the EA logs the broker response and does not retry that signal. Stop after the first accepted trade or first broker rejection.

## Manual Steps Before Any Attempt

Use `docs/trial_micro_execution_checklist.md` as the manual checkpoint.

1. Run monitor-only on Trial first.
2. Run the source scan and compile check.
3. Record the source scan PASS ID.
4. Recompile after copying files into MT5.
5. Set `BrokerServerUtcOffsetMinutes` correctly.
6. Verify EURUSD spread, stop-level, and minimum-lot metadata.
7. Attach only to the Trial Risk-Free account.
8. Use EURUSD only.
9. Confirm `EnablePropChallengeMode=false`.
10. Set `EnableTrading=true`, `EnableTrialExecution=true`, and the exact confirmation phrase only after deciding to perform the Trial micro-execution smoke.
11. Confirm SL/TP, spread, and lot size in logs.
12. Stop after the first trade or first broker rejection.
13. Disable `EnableTrialExecution` immediately afterward.

When execution is armed but no entry intent exists, the EA logs `ARMED_TRIAL_EXECUTION_WAITING_FOR_VALID_SIGNAL`. `SETUP_FORMING` logs `NO_ACTION_SIGNAL_NOT_EXECUTABLE`. Neither is an order attempt.

Do not use prop credentials in the repo. Do not run this on Surge 2 Step, Vanguard, Challenge, Verification, Funded, or any live-money account.

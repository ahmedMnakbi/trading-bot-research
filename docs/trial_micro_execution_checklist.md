# Trial Micro-Execution Checklist

Phase 13.1 is a pre-Trial safety checkpoint. It does not approve Surge 2 Step, Vanguard, Challenge, Verification, Funded, or live-money trading. It does not add symbols, pending orders, trailing stop, breakeven, retries, or Python-controlled MT5 execution.

## Before Arming Execution

Complete these steps manually before the first Trial Risk-Free micro-execution:

- Run monitor-only on the Trial Risk-Free account first and confirm no Experts or Journal errors.
- Run `python scripts/run_mql5_source_scan.py --json` and record the source scan PASS ID or saved artifact path.
- Run `python scripts/compile_mql5_ea.py --json`.
- Generate the dedicated preset with `python scripts/generate_ea_settings.py --preset trial-risk-free-eurusd-micro-execution --source-scan-pass-id <source-scan-pass-id> --broker-time-validation-note "<broker time note>"`.
- Copy the updated EA files into the MT5 data folder and recompile in MetaEditor after copying.
- Set `BrokerServerUtcOffsetMinutes` correctly after checking the broker server time against UTC.
- Fill `BrokerTimeValidationNote` with a short note confirming how the broker server UTC offset was checked.
- Verify `EURUSD` symbol mapping, session availability, spread, `SYMBOL_TRADE_STOPS_LEVEL`, `SYMBOL_VOLUME_MIN`, `SYMBOL_VOLUME_STEP`, `SYMBOL_TRADE_TICK_SIZE`, and `SYMBOL_TRADE_TICK_VALUE`.
- Confirm the EA is attached only to the Trial Risk-Free account.
- Confirm Surge 2 Step and Vanguard charts/accounts are not running the EA.
- Confirm `EnablePropChallengeMode=false`.
- Confirm `AllowedSymbols=EURUSD`.
- Confirm `MaxTradesPerDay=1`, `MaxOpenPositionsTotal=1`, and `MaxOpenPositionsPerSymbol=1`.
- Confirm `StopLossRequired=true`, `MinHoldSeconds=180`, `RiskPerTradePct<=0.25`, and `MaxRiskPerTradePct<=0.50`.

## Arming Inputs

Execution remains disabled unless all arming inputs are set intentionally:

- `AccountProgram=TrialRiskFree`
- `AccountStage=Trial`
- `EnableTrading=true`
- `EnableTrialExecution=true`
- `EnablePropChallengeMode=false`
- `ManualConfirmationText=I_ACCEPT_TRIAL_RISK_FREE_EXECUTION_ONLY`
- `SourceScanPassId` is non-empty
- `BrokerTimeValidationNote` is non-empty after the broker UTC offset is verified

If any gate fails, the EA logs the exact blocking gate. If all execution gates are armed but no entry signal exists, it logs `ARMED_TRIAL_EXECUTION_WAITING_FOR_VALID_SIGNAL`. If the signal is `SETUP_FORMING`, it logs `NO_ACTION_SIGNAL_NOT_EXECUTABLE`.

If MT5 reports init code `32767`, see `docs/troubleshooting.md` and search the Experts log for `GATE_FAIL_`.

## Stop Conditions

Stop immediately after the first accepted trade or first broker rejection:

- Save raw Experts and Journal logs.
- Save the settings used.
- Disable `EnableTrialExecution` immediately afterward.
- Return to monitor-only settings.
- Do not retry the signal manually.
- Do not attach to Surge 2 Step, Vanguard, Challenge, Verification, Funded, or live-money accounts.

This checklist is safety evidence only. It is not a profitability claim and not approval for protected account use.

# EA Settings Generator

Phase 7 adds Python support tooling for generating native MQL5 EA `.set` files. Python remains support-only and is not the prop-account execution layer.

## Safe Default

Use:

```powershell
python scripts/generate_ea_settings.py --stage Trial --output-path data/processed/ea_settings/trial_monitor_only.set
```

The default preset is Trial Risk-Free with execution disabled: `AccountProgram=TrialRiskFree`, `AccountStage=Trial`, `EnableTrading=false`, `EnableTrialExecution=false`, and `EnablePropChallengeMode=false`. It is intended for monitor-only platform testing and audit packaging unless the user later performs a separately approved Trial micro-execution smoke.

## Trial Micro-Execution Preset

Phase 13.2 adds a dedicated preset for the first Trial Risk-Free EURUSD micro-execution smoke:

```powershell
python scripts/generate_ea_settings.py `
  --preset trial-risk-free-eurusd-micro-execution `
  --source-scan-pass-id <source-scan-pass-id> `
  --broker-time-validation-note "Broker server time checked against UTC; offset is +120 minutes for this run"
```

The preset refuses to generate without a non-empty `SourceScanPassId` and a non-empty `BrokerTimeValidationNote`. The note is required because the native EA blocks Trial micro-execution unless the operator has manually verified `BrokerServerUtcOffsetMinutes`. It also refuses `Surge2Step`, `Vanguard`, `Custom`, `Challenge`, `Verification`, and `Funded`.

The generated `.set` arms only the Trial Risk-Free EURUSD path:

- `AccountProgram=ACCOUNT_PROGRAM_TRIAL_RISK_FREE`
- `AccountStage=ACCOUNT_STAGE_TRIAL`
- `EnableTrading=true`
- `EnableTrialExecution=true`
- `EnablePropChallengeMode=false`
- `ManualConfirmationText=I_ACCEPT_TRIAL_RISK_FREE_EXECUTION_ONLY`
- `AllowedSymbols=EURUSD`
- `BrokerServerUtcOffsetMinutes=120`
- `RequireBrokerTimeValidation=true`
- `BrokerTimeValidationNote=<operator note confirming the broker UTC offset>`
- `UseSpreadFilter=true`
- `MaxSpreadPoints=30`
- `SpreadUnknownBlocksTrading=true`
- `MinHoldSeconds=180`
- `StopLossRequired=true`
- `RiskPerTradePct=0.25`
- `MaxRiskPerTradePct=0.50`
- `MaxTradesPerDay=1`
- `MaxOpenPositionsTotal=1`
- `MaxOpenPositionsPerSymbol=1`
- `LogThrottleSkips=false`

This `.set` is not approval for Surge 2 Step, Vanguard, Challenge, Verification, Funded, or live-money trading. Use it only after the Trial micro-execution checklist is complete, stop after the first accepted trade or first broker rejection, and immediately set `EnableTrialExecution=false` afterward.

## Strategy Tester Simulated Execution Presets

Phase 14 adds research-only Strategy Tester presets:

```powershell
python scripts/generate_ea_settings.py --preset strategy-tester-eurusd-m5-orb --json
python scripts/generate_ea_settings.py --preset strategy-tester-eurusd-m5-vwap --json
python scripts/generate_ea_settings.py --preset strategy-tester-nacusd-c-m5-ny-m15-sweep-reclaim --json
python scripts/generate_ea_settings.py --preset strategy-tester-nacusd-c-m5-ny-m15-sweep-reclaim-relaxed-m15-direction --json
python scripts/generate_ea_settings.py --preset strategy-tester-nacusd-c-m5-ny-m15-sweep-reclaim-reclaim-hold-entry --json
python scripts/generate_ea_settings.py --preset strategy-tester-nacusd-c-m5-ny-m15-sweep-reclaim-relaxed-m15-reclaim-hold-entry --json
python scripts/generate_ea_settings.py --preset strategy-tester-spcusd-c-m5-ny-m15-sweep-reclaim --json
```

These presets generate `.set` files for MT5 Strategy Tester only:

- `EnableTrading=false`
- `EnableTrialExecution=false`
- `StrategyTesterExecutionMode=true`
- `EnablePropChallengeMode=false`
- `AccountProgram=ACCOUNT_PROGRAM_TRIAL_RISK_FREE`
- `AccountStage=ACCOUNT_STAGE_MONITOR_ONLY`
- `AllowedSymbols=EURUSD`, `NACUSD.c`, or `SPCUSD.c` depending on the approved
  research tester preset
- `StrategyTimeframe=PERIOD_M5`
- ORB preset: `StrategySelection=STRATEGY_OPENING_RANGE_BREAKOUT`
- VWAP preset: `StrategySelection=STRATEGY_VWAP_TREND_CONTINUATION`
- NYM15SR presets: `StrategySelection=STRATEGY_NY_M15_SWEEP_RECLAIM`
- NACUSD relaxed M15 direction variant:
  `NYM15SRRequireM15DirectionAgreement=false`
- NACUSD reclaim-hold entry variant:
  `NYM15SRRequireReclaimBreakoutEntry=false`

The EA refuses `StrategyTesterExecutionMode=true` unless MT5 reports Strategy Tester runtime. These presets are not Trial live-chart settings, not Surge 2 Step or Vanguard settings, and not approval for protected account use.

## Protected Stages

Challenge, Verification, and Funded settings are rejected unless approval metadata is supplied:

- trial evidence ID
- source scan PASS ID
- compile PASS ID
- final audit package ID
- human approval ID
- account program rules review ID

Surge 2 Step settings are marked rule-unverified and protected/active use is blocked until exact Surge 2 Step rules are reviewed and encoded. Vanguard settings remain blocked for protected/active use until exact rules, trial evidence, audit evidence, and human approval exist. Even with metadata, this project still requires current Upcomers daily reset timezone confirmation and Dynamic Risk Shield verification before protected preset use.

## Unsafe Settings

The generator rejects unsafe limits such as daily hard loss at or above 4%, overall hard loss at or above 7%, max risk per trade above 0.50%, minimum hold below 180 seconds, disabled stop-loss requirement, excessive trade/message counters, and prohibited behavior flags.

The script writes a `.set` file plus summary JSON and Markdown. Generated settings are not approval for Surge 2 Step, Vanguard, Challenge, Verification, Funded, or live use.

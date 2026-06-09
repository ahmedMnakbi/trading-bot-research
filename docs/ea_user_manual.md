# EA User Manual

The Phase 13 EA is still execution-disabled by default. It adds a tightly gated native MQL5 Trial Risk-Free micro-execution path for observing real order mechanics on the free Trial account only. It is not approved for Surge 2 Step, Vanguard, Challenge, Verification, Funded, or live-money use.

## Default Safety Inputs

- `EnableTrading=false`
- `EnableTrialExecution=false`
- `EnablePropChallengeMode=false`
- `AccountProgram=TrialRiskFree`
- `AccountStage=MonitorOnly`
- `RequireManualConfirmationText=true`
- `ManualConfirmationText=""`
- Trial execution confirmation phrase, only when explicitly approved: `I_ACCEPT_TRIAL_RISK_FREE_EXECUTION_ONLY`
- `PropDayResetTimezone=UNCONFIRMED_CONSERVATIVE`
- `MinHoldSeconds=180`
- `MaxTradesPerDay=1`
- `MaxServerMessagesPerDay=500`
- `StopLossRequired=true`
- `MaxOpenPositionsTotal=1`
- `MaxOpenPositionsPerSymbol=1`
- `AllowedSymbols=EURUSD`
- `StrategyTimeframe=PERIOD_M1`
- `OpeningRangeMinutes=15`
- `StrategySignalCooldownSeconds=900`
- `MaxSignalsPerStrategyPerSession=1`
- `BrokerTimeMode=BROKER_TIME_MANUAL_UTC_OFFSET`
- `BrokerServerUtcOffsetMinutes=0`
- `RequireBrokerTimeValidation=true`
- `BrokerTimeValidationNote=""`
- `UseSpreadFilter=true`
- `MaxSpreadPoints=30`
- `SpreadUnknownBlocksTrading=true`
- `EvaluationMode=EVALUATION_ON_NEW_CLOSED_BAR`
- `MinEvaluationSeconds=60`
- `LogThrottleSkips=false`
- internal daily hard loss guard `3.0%`
- internal overall hard loss guard `6.0%`

Prohibited behavior inputs default to false: `AllowGrid`, `AllowMartingale`, `AllowAveragingDown`, `AllowHFT`, `AllowArbitrage`, `AllowCopyTrading`, and `AllowScalpingUnder2Minutes`.

## What It Does

The EA logs startup configuration, startup validation, unresolved rule warnings, and monitor-only decisions. It runs checks for broker-time conversion, session, symbol, spread, news placeholder, prop-firm rules, daily and overall loss guards, risk, hypothetical trade intent validation, strategy selection, audit logging, and no-trade refusal unless Trial micro-execution is explicitly armed.

Broker server time is converted to UTC using `BrokerServerUtcOffsetMinutes`, then UTC is converted to America/New_York using U.S. daylight-saving rules. The user must verify the broker offset and symbol sessions in MT5 before any Trial monitor-only observation.

The spread gate reads `SYMBOL_SPREAD` or falls back to ask/bid metadata. Unknown spread blocks monitor signals by default. Excessive spread returns `SKIP_SPREAD`; it does not place or modify orders.

The default evaluation mode is `OnNewClosedBar`, with a minimum spacing of 60 seconds. Repeated ticks on the same closed bar are suppressed by default with `LogThrottleSkips=false`; they still increment throttle counters and do not inflate monitor evaluation counters. Turn throttle-skip logging on only for short debugging windows.

Strategy modules produce signal/intention records only. Every strategy decision is intended to use closed bars only and carry strategy name, symbol, symbol class, timeframe, direction, state, server timestamp, New York timestamp when available, session tag, reason codes, suggested entry when applicable, suggested stop-loss/take-profit when applicable, minimum-hold-until timestamp, spread/filter status, volume type when applicable, and a monitor-only note.

- Opening Range Breakout builds the range from M1 bars, converts minutes to M1 bars, defaults to BreakThenRetest mode, suggests a stop-loss from retest/breakout structure, and suppresses repeated same-session signals.
- VWAP Trend Continuation uses closed M5 bars, requires directional control, VWAP slope, impulse, pullback near VWAP, and rejection confirmation.
- Dynamic Noise-Band Momentum plus VWAP Stop is a derived engineered rule set using VWAP-centered ATR/StdDev bands, compression, expansion, and normalized momentum.
- London/New York Overlap Momentum is FX/gold-focused by default, blocks U.S. index CFDs unless a later phase adds explicit approval, and uses the 07:00-08:00 New York reference range with 08:00-12:00 New York window.
- Volume/Volatility Expansion builds a setup box from closed bars, requires contraction, range expansion, and volume expansion, and logs real-volume or tick-volume usage.

Counter semantics are separated: monitor evaluations count local observations, trade intents count strategy entry/exit intentions, refused trade actions count no-trade `TradeManager` refusals, and actual server/order messages remain zero in monitor-only mode. Routine `WAIT`, `SKIP_*`, and `SETUP_FORMING` states do not produce repeated `TradeManager` warnings.

Trial micro-execution is available only through the isolated native MQL5 `TrialExecution` module. It can send a market order only when all gates pass: `AccountProgram=TrialRiskFree`, `AccountStage=Trial`, `EnableTrading=true`, `EnableTrialExecution=true`, `EnablePropChallengeMode=false`, exact manual confirmation text, source scan PASS marker, `StopLossRequired=true`, `MinHoldSeconds>=180`, `RiskPerTradePct<=0.25`, `MaxRiskPerTradePct<=0.50`, one total position, one position per symbol, one trade per day, `AllowedSymbols=EURUSD`, spread filter enabled, current spread within `MaxSpreadPoints`, and strategy signal `ENTER_LONG_INTENT` or `ENTER_SHORT_INTENT` with valid SL/TP. It sends no pending orders, performs no scaling, makes no retry loop, and logs broker response details.

If MT5 returns init code `32767`, open the Experts log and search for `GATE_FAIL_`. The Trial micro preset requires a non-empty `BrokerTimeValidationNote` after manually verifying `BrokerServerUtcOffsetMinutes`; protected-account approval IDs are not Trial Risk-Free micro gates.

## Strategy Tester Simulation

`StrategyTesterExecutionMode=false` by default. When set to `true`, it can initialize only inside MT5 Strategy Tester runtime and must keep `EnableTrading=false`, `EnableTrialExecution=false`, and `EnablePropChallengeMode=false`. Simulated tester orders are for historical strategy research only. They do not approve Trial live-chart execution, Surge 2 Step, Vanguard, Challenge, Verification, Funded, or live-money use.

Challenge, Verification, and Funded stages require trial evidence ID, source scan PASS ID, compile PASS ID, final audit package ID, explicit human approval ID, daily reset timezone confirmation ID, and Dynamic Risk Shield confirmation ID.

## What It Does Not Do

By default it does not place orders, open positions, close positions, modify stops, trade Trial Risk-Free, Surge 2 Step, Vanguard, or any protected account, use prop credentials, log into MT5, or enable Python-controlled execution. The only exception is the explicitly armed Trial Risk-Free micro-execution path described above, and that path is not prop challenge approval.

Trial Risk-Free 10K testing is the first MT5 platform testing environment. Trial behavior is not approval for Surge 2 Step, Vanguard, or funded trading. Surge 2 Step 5K is rule-unverified and blocked until its exact rules are reviewed and encoded. Vanguard 2K remains blocked until exact rules, trial evidence, audit package, and human approval exist.

Daily loss reset timezone must be confirmed from current Upcomers rules before challenge use. Exact Dynamic Risk Shield calculation must also be verified before challenge presets are enabled.

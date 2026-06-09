# MQL5 Source Scanning

MQL5 source scanning is a local static check for the native EA source tree. It does not compile, run, attach, trade, or log into MT5.

Use:

```powershell
python scripts/run_mql5_source_scan.py
```

If no `mql5/` tree exists, the result is `SKIPPED`. From Phase 4 onward the tree exists, so missing required safety guards are `FAIL`.

The scanner detects prohibited terms and patterns:

- martingale
- grid
- averaging down
- hft
- arbitrage
- copy trading
- sub-2-minute scalping

It also checks for future required guard markers:

- `EnableTrading=false`
- `EnableTrialExecution=false`
- `StrategyTesterExecutionMode=false`
- manual confirmation
- account-stage guard
- approval metadata guard
- `PropDayResetTimezone`
- Dynamic Risk Shield blocker
- `UNKNOWN_RULE_BLOCK`
- `MinHoldSeconds`
- `MaxTradesPerDay`
- trade-action counter
- `MaxServerMessagesPerDay`
- `StopLossRequired`
- daily loss guard
- overall loss guard
- no-trade `TradeManager`
- Phase 6 strategy signal types
- entry-intent stop-loss guard
- strategy session gating
- strategy cooldown guard
- no current-bar signal-decision markers where detectable
- closed-bar-only markers
- ORB M1 range build and minutes-to-bars handling
- ORB BreakThenRetest reason markers
- VWAP impulse, pullback, slope, and rejection markers
- real-volume and tick-volume fallback markers
- per-session strategy signal caps
- broker server UTC offset inputs
- DST-aware America/New_York conversion markers
- half-hour session boundary markers
- real spread gate markers
- OnTick/OnTimer throttling markers
- counter-semantics markers for monitor evaluations, intents, refused actions, and server messages
- Trial Risk-Free micro-execution isolation and gate markers
- Strategy Tester simulated execution isolation and runtime gate markers
- no-retry markers for isolated order sends

The scanner fails MQL5 order-placement calls such as direct send requests, trade library use, buy/sell calls, position open calls, and pending-order helpers unless the call is inside an isolated execution module:

- `mql5/Include/UpcomersNYSessionPropBot/TrialExecution.mqh`
- `mql5/Include/UpcomersNYSessionPropBot/TesterExecution.mqh`

`TrialExecution.mqh` is scanned for TrialRiskFree-only gates, exact manual confirmation, source scan marker, EURUSD-only defaults, one-trade/one-position caps, required SL/TP, spread filtering, market-order-only behavior, and no retry loop.

`TesterExecution.mqh` is scanned for `MQL_TESTER` runtime gating, `StrategyTesterExecutionMode=true`, `EnableTrading=false`, `EnableTrialExecution=false`, `EnablePropChallengeMode=false`, TrialRiskFree/MonitorOnly scope, EURUSD-only defaults, required SL/TP, spread filtering, market-order-only behavior, and no retry loop.

Explicit prohibited-input names such as `AllowGrid=false`, `AllowMartingale=false`, `AllowArbitrage=false`, and `AllowCopyTrading=false` are allowlisted only when they are used as disabled safety flags.

The Phase 14 EA is expected to pass this scan with execution disabled by default and exactly two allowed order-call locations: Trial live micro-execution in `TrialExecution.mqh` and Strategy Tester simulated execution in `TesterExecution.mqh`. A scan PASS is still not evidence that the user's broker offset is correct; that must be verified in MT5 before Trial observation, Trial micro-execution, or interpreting Strategy Tester session results.

A scan PASS is not approval for Surge 2 Step, Vanguard, Challenge, Verification, Funded, live-money use, or protected account use. It also is not proof that a Trial micro-execution should be run; the user must still manually verify the settings and stop after the first trade or first broker rejection.

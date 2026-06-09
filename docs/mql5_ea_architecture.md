# MQL5 EA Architecture

Phase 13 keeps the native MQL5 EA execution-disabled by default and adds a tightly gated Trial Risk-Free micro-execution module for observing real order mechanics on the free Trial account only. It is not approved for Surge 2 Step, Vanguard, Challenge, Verification, Funded, live-money use, or any prop deployment.

## Source Layout

- `mql5/Experts/UpcomersNYSessionPropBot/UpcomersNYSessionPropBot.mq5` is the EA entrypoint.
- `mql5/Include/UpcomersNYSessionPropBot/` contains configuration, logging, guard, strategy, state, and monitor stubs.
- `mql5/Include/UpcomersNYSessionPropBot/TrialExecution.mqh` is the isolated Trial Risk-Free live micro-execution module.
- `mql5/Include/UpcomersNYSessionPropBot/TesterExecution.mqh` is the isolated MT5 Strategy Tester simulated execution module.
- Source scanning fails order calls anywhere outside those isolated modules.

## Runtime Flow

`OnInit` loads safe inputs, logs the startup configuration, validates compliance settings, writes unresolved-rule audit warnings, and starts a timer only when configuration is safe enough for monitor-only operation. Unsafe settings return `INIT_PARAMETERS_INCORRECT`.

`OnTick` and `OnTimer` first pass through `StateManager.ShouldEvaluateMonitorEvent`. The default `EvaluationMode=OnNewClosedBar` with `MinEvaluationSeconds=60` avoids repeated per-tick strategy evaluation. When an event is skipped, the EA logs a throttle reason and does not count a monitor evaluation.

Accepted evaluations run session, symbol, spread, news placeholder, account stage, daily loss, overall loss, risk, hypothetical trade intent, strategy selection, and audit logging. With default inputs, strategy decisions are still refused by `TradeManager`.

`TradeManager` remains a no-trade stub for monitor-only, Surge 2 Step, Vanguard, Challenge, Verification, Funded, and any non-TrialRiskFree mode. `WAIT`, skip, and setup evaluations do not count as trade attempts or server/order messages. Entry and exit intents count as monitor-only intent events and refused trade actions unless Trial micro-execution is explicitly armed.

`TrialExecution` can process only `ENTER_LONG_INTENT` or `ENTER_SHORT_INTENT` with valid SL/TP. It requires `AccountProgram=TrialRiskFree`, `AccountStage=Trial`, `EnableTrading=true`, `EnableTrialExecution=true`, `EnablePropChallengeMode=false`, exact manual confirmation `I_ACCEPT_TRIAL_RISK_FREE_EXECUTION_ONLY`, a source scan PASS marker, EURUSD-only allowed symbols, one trade per day, one open position, one position per symbol, spread filter pass, and risk caps. It sends a single market request with attached SL/TP and no retry loop, then logs broker response details.

## Strategy Layer

`StrategyBase` defines signal-only results: `WAIT`, `SETUP_FORMING`, entry intents, exit intent, session/data/spread/news skips, and session close. Results include strategy name, symbol, symbol class, timeframe, direction, reason codes, server timestamp, New York timestamp when available, session tag, suggested entry, optional take-profit, required stop-loss for entry intents, minimum-hold-until timestamp, spread/filter status, volume type when applicable, monitor-only note, and a simple quality score.

Opening Range Breakout and VWAP Trend Continuation can emit monitor-only entry intents when objective criteria are met. Dynamic Noise-Band Momentum, London/New York Overlap Momentum, and Volume/Volatility Expansion now contain objective monitor-only signal rules as well. Entry intents are not trades. They are logged and then refused by `TradeManager`.

All strategy modules use closed-bar-only markers and duplicate-setup suppression. The default per-strategy/per-session cap is one signal. The source scanner enforces the main strategy markers.

## Session Conversion Boundary

`SessionManager` defines the target New York windows:

- U.S. index cash: 09:30-16:00 America/New_York.
- FX/gold/crypto New York session: 08:00-17:00 America/New_York.
- London/New York overlap: 08:00-12:00 America/New_York, with the reference range at 07:00-08:00.

The EA does not assume broker server time equals New York time. `BrokerTimeMode=BROKER_TIME_MANUAL_UTC_OFFSET` and `BrokerServerUtcOffsetMinutes` explicitly convert server timestamps to UTC. `SessionManager` then applies U.S. New York DST rules: DST starts at 07:00 UTC on the second Sunday in March and ends at 06:00 UTC on the first Sunday in November.

This implementation is suitable for current-session gating, but the user must verify the broker server offset and symbol sessions inside MT5 before relying on filters for Trial monitor-only observation. Historical broker-specific server-time changes are not inferred.

## Spread Gate

`SymbolManager` reads `SYMBOL_SPREAD` and falls back to ask/bid plus point size when needed. Defaults are `UseSpreadFilter=true`, `MaxSpreadPoints=30`, and `SpreadUnknownBlocksTrading=true`. Unknown or excessive spread returns `SIGNAL_SKIP_SPREAD` in monitor-only mode and does not place orders.

## Phase 13 Boundaries

- Execution disabled by default with `EnableTrading=false` and `EnableTrialExecution=false`.
- Native order calls exist only in `TrialExecution.mqh` and `TesterExecution.mqh`.
- `StrategyTesterExecutionMode=false` by default and can activate only when MT5 reports `MQL_TESTER`.
- Trial execution is free TrialRiskFree only and stops after the first trade or first broker rejection.
- No Surge 2 Step, Vanguard, Challenge, Verification, Funded, or live-money approval.
- No Python-controlled MT5 prop execution.
- No grid, martingale, averaging down, HFT, arbitrage, copy trading, or sub-2-minute scalping logic.
- No pending orders, scaling, repeated retries, trailing stop, breakeven modification, or early close before `MinHoldSeconds` except future emergency hard-stop/risk-reduction logic.

Account programs are tracked separately from stages: `TrialRiskFree`, `Vanguard`, `Surge2Step`, and `Custom`. Surge 2 Step is rule-unverified and not encoded. Vanguard is protected until exact rules, trial evidence, audit package, and approval metadata exist. Protected account stages require trial evidence, source scan PASS, compile PASS, final audit package ID, explicit human approval metadata, daily reset timezone confirmation, and Dynamic Risk Shield confirmation.

Daily loss reset timezone remains configurable through `PropDayResetTimezone`; it is not assumed to be UTC. Until current Upcomers rules confirm the reset timezone, protected stages remain blocked. The exact Dynamic Risk Shield calculation is also unresolved and blocks challenge presets.

# Prop Firm Compliance Mode

Phase 13 keeps prop-firm compliance blocking in place and adds a native MQL5 Trial Risk-Free micro-execution path for the free Trial account only. It does not enable Surge 2 Step, Vanguard, Challenge, Verification, Funded, live-money trading, prop credentials, MT5 login, or Python-controlled MT5 execution.

## Guard Model

Startup validation rejects unsafe settings before the timer starts. The EA refuses active configuration when `EnableTrading=true` or `EnableTrialExecution=true` is supplied without the exact required confirmation text and TrialRiskFree gates. `TradeManager` still refuses execution for monitor-only, Surge 2 Step, Vanguard, protected stages, and any non-TrialRiskFree mode.

Protected stages are `Challenge`, `Verification`, and `Funded`. They require all of these IDs:

- trial evidence ID
- source scan PASS ID
- compile PASS ID
- final audit package ID
- explicit human approval ID
- daily reset timezone confirmation ID
- Dynamic Risk Shield confirmation ID

`TrialRiskFree` is the first MT5 platform testing environment. Trial evidence is not approval for Surge 2 Step, Vanguard, or funded trading. `Surge2Step` is rule-unverified and blocked until exact rules are reviewed and encoded. `Vanguard` remains protected until exact rules, trial evidence, audit package, and explicit human approval metadata exist.

## Loss And Risk Limits

The internal hard daily loss guard defaults to `3.0%`, below the 4% prop cap. The internal hard overall loss guard defaults to `6.0%`, below the 7% prop cap. Startup validation rejects daily hard loss at or above `4.0%`, overall hard loss at or above `7.0%`, soft limits at or above hard limits, `RiskPerTradePct > MaxRiskPerTradePct`, and `MaxRiskPerTradePct > 0.50%`.

`PropDayResetTimezone` is configurable and defaults to `UNCONFIRMED_CONSERVATIVE`. The project must confirm the current Upcomers daily loss reset timezone before challenge use. Until confirmed, protected stages remain blocked.

The exact Dynamic Risk Shield calculation is also unresolved. Challenge, Verification, and Funded presets must not be enabled until that calculation is verified from current Upcomers rules and captured by approval metadata.

## Counters And Refusals

The EA tracks daily trade-action requests and server-message requests. Defaults are `MaxTradesPerDay=1` and `MaxServerMessagesPerDay=500`; Trial micro-execution requires one trade per day and one open position.

`MinHoldSeconds` must stay at least `180`. A future close request before the minimum hold is refused unless it is explicitly an emergency hard-stop risk-reduction path.

`StopLossRequired=true` is mandatory. Position caps default to `MaxOpenPositionsTotal=1` and `MaxOpenPositionsPerSymbol=1`. Trial micro-execution also requires `AllowedSymbols=EURUSD`, valid SL/TP on the strategy entry intent, spread filter pass, and source scan PASS marker.

## Remaining Blockers

Before protected-stage work, the repo still needs current Upcomers rule confirmation for daily reset timezone and Dynamic Risk Shield behavior. It also needs formal trial evidence, source scan PASS, compile PASS, final audit package ID, and explicit human approval metadata. Phase 13 Trial micro-execution is smoke evidence only unless later formal evidence is collected and verified.

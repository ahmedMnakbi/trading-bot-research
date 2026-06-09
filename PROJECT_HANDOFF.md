# PROJECT_HANDOFF.md

Last updated: 2026-06-03

This handoff is for an AI assistant that has never seen this repository. It
contains project history, current status, safety boundaries, implementation
details, and the recommended next plan. Do not treat this document as approval
to trade. It is an engineering handoff only.

## 1. Project Summary

This project is a safety-first trading research and native MetaTrader 5 Expert
Advisor project for an Upcomers prop-firm context.

The intended final outcome is a native MQL5 EA named
`UpcomersNYSessionPropBot` that can be reviewed, compiled, scanned, tested in
MT5 Strategy Tester, observed safely on the Trial Risk-Free MT5 account, and
only much later considered for protected prop-firm account stages after rule
review, evidence, audit packaging, and explicit human approval.

The project began as a non-live Python trading research framework with public
market data ingestion, deterministic backtesting, paper trading, reporting,
safety audits, release checks, and operator tooling. That Python foundation is
still useful, but it is no longer the execution direction for prop-firm use.
The current primary product direction is a native MQL5 EA.

Hard boundary:

- Native MQL5 EA code is the only permitted prop-firm execution path.
- Python is support-only: research, validation, reporting, scanning, settings
  generation, log parsing, audit packaging, and evidence workflows.
- Python-controlled MT5 execution is quarantined and not allowed for Challenge,
  Verification, Funded, Surge 2 Step, Vanguard, or other prop deployment.
- Trading is disabled by default.
- Surge 2 Step, Vanguard, Challenge, Verification, Funded, and live-money use
  are blocked.

The only real order path currently present is an isolated, disabled-by-default,
tightly gated Trial Risk-Free micro-execution path in
`mql5/Include/UpcomersNYSessionPropBot/TrialExecution.mqh`. It is for observing
one safe Trial Risk-Free order mechanic only, not for prop challenge use. There
is also an isolated Strategy Tester simulated execution path in
`mql5/Include/UpcomersNYSessionPropBot/TesterExecution.mqh`.

## 2. Trading Context

The target platform is MetaTrader 5. The current broker/account context is
Upcomers MT5 with three account programs known to this project:

- Trial Risk-Free 10K: first MT5 platform testing environment.
- Surge 2 Step 5K: future challenge-style account, rule-unverified and blocked.
- Vanguard 2K: protected future account, not approved for bot use.

No account numbers, passwords, broker login IDs, API keys, or prop credentials
should be stored in this repository.

Target account-program model:

- `AccountProgram = TrialRiskFree | Vanguard | Surge2Step | Custom`
- `AccountStage = MonitorOnly | Trial | Challenge | Verification | Funded`

Current target symbol and timeframe:

- Primary symbol: `EURUSD`
- Current tester/live-chart focus: `M5`
- Some ORB range construction uses closed `M1` bars.
- Default EA `StrategyTimeframe` in the source is `PERIOD_M1`; generated
  Strategy Tester presets use `PERIOD_M5`.

Execution model:

- Default live-chart mode: monitor-only, no orders.
- Trial micro-execution: one isolated live Trial Risk-Free market order path,
  disabled by default and guarded by many inputs.
- Strategy Tester simulated execution: allowed only inside MT5 Strategy Tester
  runtime when `StrategyTesterExecutionMode=true`; it must not activate on live
  charts.
- Surge 2 Step, Vanguard, Challenge, Verification, Funded, and live-money
  execution: not approved and blocked.

Live/demo/backtest status:

- Python non-live research and backtesting framework exists.
- Native MQL5 EA compiles.
- Native EA source scan passes as of the last known verification.
- Trial monitor-only smoke testing has occurred informally.
- Trial formal observation evidence is incomplete/skipped.
- Trial micro-execution was armed once for observation and produced no accepted
  trade, no broker rejection, and no repeated order attempts.
- Strategy Tester simulated execution now sends simulated orders successfully
  in tester runtime.
- No protected prop-firm account is approved for bot use.

## 3. Current Project Goal

The project is currently just after Phase 14.5.

The immediate goal is to make Strategy Tester research results repeatable and
evidence-driven:

1. Export MT5 Strategy Tester reports/logs for ORB and VWAP runs.
2. Collect each run into a local evidence package.
3. Parse balances, trades/deals, diagnostics, and tester execution summaries.
4. Compare ORB vs VWAP using a small, non-optimized test matrix.
5. Keep all conclusions research-only.

The next assistant should not expand live Trial execution, add symbols, add
pending orders, add retries, add trailing stops, add breakeven logic, optimize
parameters, or enable Surge/Vanguard/protected stages.

## 4. How We Got Here

Chronological history:

1. The project started as a Python trading-bot research framework. It used
   public market data, local cached candles, deterministic backtesting, paper
   trading, reporting, readiness checks, and safety audits. It was explicitly
   non-live.

2. The project added non-live operational tooling: config validation, kill
   switch behavior, safety requirements, fixture data, artifact registries,
   release packaging, incident replay, and operator workflows.

3. The direction changed when the target became an Upcomers/MT5 prop-firm
   workflow. A critical decision was made: Python must not be the prop-firm
   execution layer. Python MT5 execution was quarantined as legacy and
   non-prop-compatible.

4. The repository established the direction lock: native MQL5 EA is the only
   final prop-firm execution path. Trial Risk-Free is the first MT5 platform
   testing environment, but it is not approval for Surge 2 Step, Vanguard, or
   funded trading.

5. Account-program awareness was added. The project no longer assumes Vanguard
   is the only future prop account. It tracks TrialRiskFree, Surge2Step,
   Vanguard, and Custom.

6. Early MT5 support stayed read-only: MT5 historical rates cache, New York
   session research, local validation, campaigns, reports, and audits.

7. A native MQL5 EA tree was created under `mql5/`. It started monitor-only and
   trading-disabled. The EA had safe inputs, startup logging, account-stage
   guards, unresolved-rule warnings, and no order calls.

8. Strategy modules were built as signal generators. They produced monitor-only
   states such as `WAIT`, `SETUP_FORMING`, `ENTER_LONG_INTENT`, and
   `ENTER_SHORT_INTENT`. `TradeManager` refused execution by default.

9. Session and spread plumbing were hardened. The EA stopped assuming broker
   time equals New York time. It added `BrokerServerUtcOffsetMinutes` and a
   DST-aware America/New_York conversion. Spread checks read broker metadata
   and block unknown/excessive spread by default.

10. Trial monitor-only smoke testing began. A first Trial Risk-Free EURUSD M5
    smoke run lasted about 27 minutes. Observed: zero orders, zero positions,
    no Experts errors, no Journal errors, monitor-only logs present, strategy
    logs present, expected unresolved-rule warnings present. This was packaged
    as smoke-only informal evidence because raw logs and required notes were
    missing.

11. Log spam from throttle skips was fixed. Routine
    `THROTTLE_MIN_SECONDS` skip logs are suppressed by default using
    `LogThrottleSkips=false`, while startup, monitor summaries, blocks, and
    strategy diagnostics remain visible.

12. Formal Trial evidence workflow was clarified. Screenshots are optional,
    but raw Experts/Journal logs and notes are required for formal evidence.
    Edited/cleaned excerpts are smoke-only or informal.

13. A tightly gated Trial Risk-Free micro-execution path was added. It requires
    TrialRiskFree, Trial stage, exact manual confirmation, source scan marker,
    broker-time validation note, EURUSD-only, one trade/day, one position, SL/TP,
    spread filter, and strict risk caps. It sends one market order with attached
    SL/TP and no retry loop. It is disabled by default.

14. Trial micro-execution initialization initially failed with MT5 code 32767.
    Startup gate diagnostics were added so each failed gate logs
    `GATE_FAIL_<NAME>`, input value, expected value, and applicability. The
    Trial micro path does not require protected-stage approval IDs such as
    `HumanApprovalId` or `FinalAuditPackageId`.

15. The user ran an armed Trial Risk-Free micro-execution observation for about
    two hours on EURUSD M5. Observed: no accepted trade, no broker rejection,
    no repeated order attempts. The EA stayed armed and waited for
    `ENTER_LONG_INTENT` or `ENTER_SHORT_INTENT`.

16. Strategy Tester simulated execution mode was added. It is separate from
    Trial live-chart execution, requires actual MT5 tester runtime, and must
    keep `EnableTrading=false` and `EnableTrialExecution=false`.

17. Strategy Tester compile and signature mismatches were fixed after Phase 14.
    The call signatures for `TrialExecutionManager::ProcessDecision` and
    `TesterExecutionManager::ProcessDecision` were aligned.

18. Tester presets were corrected. ORB preset selects
    `STRATEGY_OPENING_RANGE_BREAKOUT`; VWAP preset selects
    `STRATEGY_VWAP_TREND_CONTINUATION`. MT5 sometimes visually retained an old
    input after loading a `.set`; docs now say the `.set` and summary JSON are
    the source of truth.

19. Tester diagnostics were added. The EA logs
    `STRATEGY_DIAGNOSTICS_SUMMARY`, `TESTER_ENTRY_INTENT_RECEIVED`,
    `TESTER_ORDER_REQUEST`, `TESTER_EXECUTION_SUMMARY`, gate failures, broker
    responses, retcodes, filling mode, stop levels, volume metadata, bid/ask,
    point, and digits.

20. Strategy Tester order rejection was diagnosed and fixed. The likely problem
    was invalid or broker-incompatible order request values such as unsupported
    filling mode, unnormalized price/SL/TP, or volume step handling. The tester
    execution module now normalizes price, SL/TP, and volume, derives filling
    mode from broker metadata, and logs full request/result metadata.

21. Strategy Tester execution now works. User-reported observations:
    VWAP EURUSD M5 from 2026-04-01 to 2026-06-01 sent 40/40 simulated tester
    orders, rejected 0, final balance 9992.08 from 10000.00, approximate
    result -7.92 USD. ORB over the same range sent 42 simulated tester orders,
    rejected 0, final balance 9996.37 from 10000.00, approximate result
    -3.63 USD. These are research observations, not formal evidence until raw
    reports/logs are collected, and not profitability claims.

22. Phase 14.5 added result packaging and comparison tooling:
    `parse_strategy_tester_report.py`, `collect_strategy_tester_evidence.py`,
    and `compare_strategy_tester_runs.py` can parse, package, and compare
    Strategy Tester runs without screenshots.

Problems solved:

- Python MT5 execution quarantined from prop-compatible workflows.
- Native EA source tree exists and compiles.
- MQL5 source scanner enforces safety markers and order-call isolation.
- Trial micro-execution gates are explicit and diagnosable.
- Routine throttle log spam is suppressed.
- Strategy Tester simulated execution can now send simulated orders.
- Parser/collector/comparator can package tester evidence locally.

Problems remaining:

- Exact Upcomers daily reset timezone is still unconfirmed.
- Exact Dynamic Risk Shield calculation is still unverified.
- Surge 2 Step exact rules are not encoded.
- Vanguard exact rules are not encoded.
- Formal Trial observation evidence is incomplete/skipped.
- Strategy Tester reports/logs for the latest ORB/VWAP results still need to be
  exported and packaged through the new tools.
- Strategy performance is not proven; the latest observed ORB/VWAP backtests
  were slightly negative.
- Broker-specific behavior still needs manual review before any further Trial
  execution attempt.

## 5. Project Phases

| Phase | Goal | Completed | Remains | Status | Relevant files |
| --- | --- | --- | --- | --- | --- |
| Original Python tasks 1-15 | Build non-live research, backtesting, paper trading, reporting, safety audit, and release tooling | Public data ingestion, deterministic backtests, paper trading, reports, incident replay, release checks | Keep as support infrastructure only | Completed for non-live scope | `src/trading_bot/`, `tests/`, `docs/`, `scripts/check_all.py` |
| Phase 0 cleanup and direction lock | Quarantine Python MT5 execution and state native EA direction | Python MT5 execution marked legacy/non-prop-compatible, direction lock established | Keep scanner enforcing boundary | Completed | `docs/upcomers_native_ea_direction_lock.md`, `AGENTS.md`, source scanner |
| Phase 1 docs/config/tests alignment | Align docs/config/tests with native MQL5 EA objective | README, safety docs, MT5 docs, config updated | Maintain wording as phases evolve | Completed | `README.md`, `config/mt5_transformation.yaml`, docs |
| Phase 2 agent rules and scanning foundation | Add repo rules and scanner foundation | `AGENTS.md`, MQL5 scanner policy, tests for banned patterns and required guards | Update scanner as new safety controls appear | Completed | `AGENTS.md`, `scripts/run_mql5_source_scan.py`, `src/trading_bot/mql5/source_scan.py` |
| Phase 3 dev environment tooling | Add local install/check scripts and MetaEditor detection | Dev tools, environment checks, compile wrapper, security scan docs/tests | Keep optional tools local-only | Completed | `scripts/install_dev_tools.py`, `scripts/check_dev_environment.py`, `scripts/check_metaeditor.py`, `scripts/compile_mql5_ea.py` |
| Phase 4 EA skeleton | Create monitor-only native MQL5 source tree | EA entrypoint, config, logging, risk/session/symbol/trade/audit modules | No trading behavior in this phase | Completed | `mql5/Experts/.../UpcomersNYSessionPropBot.mq5`, `mql5/Include/...` |
| Phase 5 compliance guards | Harden prop compliance and protected-stage gates | Strict defaults, blocked protected stages, unresolved-rule warnings | Exact external rules still unresolved | Completed with unresolved-rule caveats | `Config.mqh`, `PropFirmRules.mqh`, tests `test_mql5_phase5_compliance_guards.py` |
| Phase 6 strategy signals | Add signal-only strategy modules | ORB, VWAP, noise band, London/NY overlap, volatility expansion signal contracts | Strategy quality and profitability unproven | Completed for signal generation | `OpeningRangeBreakout.mqh`, `VWAPTrendContinuation.mqh`, strategy modules |
| Phase 7 audit/report support | Add compliance/audit packaging support | Compliance reports, audit packages, evidence semantics | Need real formal evidence for later stages | Completed | `scripts/export_prop_compliance_report.py`, `scripts/export_ea_audit_package.py` |
| Phase 8 cleanup hardening | Improve hygiene and account-program language | `.gitignore`, cleanup tooling/docs, AccountProgram support, evidence semantics | Continue avoiding generated artifact churn | Completed | `.gitignore`, `docs/feature_matrix.md`, `config/mt5_transformation.yaml` |
| Phase 8.5 strategy hardening | Tighten closed-bar strategy logic and scanner checks | Closed-bar markers, ORB/VWAP/volume reason markers, signal caps | More market validation needed | Completed for current rules | `tests/test_mql5_phase8_5_strategy_hardening.py`, strategy modules |
| Phase 9 session/spread plumbing | Implement broker-time conversion, session gates, spread gate | DST-aware New York conversion, spread blocking, throttling, counters | User must verify broker offset and symbol sessions manually | Completed with manual verification required | `SessionManager.mqh`, `SymbolManager.mqh`, `StateManager.mqh` |
| Phase 10.1 throttle log hygiene | Reduce monitor-only throttle spam | `LogThrottleSkips=false`, non-actionable TradeManager warnings suppressed | Use verbose throttle logs only briefly for debugging | Completed | `StateManager.mqh`, `TradeManager.mqh`, docs |
| Phase 11 smoke evidence | Package first Trial monitor-only smoke | Smoke evidence recognized as informal/WARN | Formal raw logs and notes missing | Completed as smoke-only | `scripts/collect_trial_observation_evidence.py`, `scripts/verify_trial_observation_package.py` |
| Phase 11.1 formal evidence workflow | Make formal Trial evidence easier without screenshots | Notes template script, screenshots optional, raw logs/notes required | User skipped formal Trial evidence for now | Completed workflow, evidence incomplete | `scripts/create_trial_observation_notes.py`, docs |
| Phase 12 Strategy Tester workflow | Add tester workflow and parsing/audit support | Parser/collector, docs, monitor-only tester semantics | Needed simulated execution later | Completed | `scripts/parse_strategy_tester_report.py`, `scripts/collect_strategy_tester_evidence.py` |
| Phase 13 Trial micro-execution | Add isolated Trial Risk-Free micro-execution path | One market order path with SL/TP, no retry, disabled by default | Not approved for protected accounts | Completed but tightly restricted | `TrialExecution.mqh`, `generate_ea_settings.py` |
| Phase 13.1 pre-Trial safety checkpoint | Prove gates and no extra order calls | Tests for defaults, Trial gates, no pending orders, no retry | Manual checklist still required before any Trial attempt | Completed | `docs/trial_micro_execution_checklist.md`, tests |
| Phase 13.2 safe micro settings | Generate Trial micro `.set` preset | Requires non-empty `SourceScanPassId`, broker-time note, EURUSD-only | Must disable immediately after first trade/rejection | Completed | `scripts/generate_ea_settings.py`, `src/trading_bot/mql5/settings.py` |
| Phase 13.3 gate diagnostics | Diagnose MT5 init code 32767 failures | Explicit `GATE_FAIL_*` logs and troubleshooting docs | Continue adding gate detail if new failures appear | Completed | `UpcomersNYSessionPropBot.mq5`, `docs/troubleshooting.md` |
| Phase 14 Strategy Tester execution | Add tester-only simulated execution | Isolated `TesterExecution.mqh`, tester runtime gate, presets | Research-only, not live approval | Completed | `TesterExecution.mqh`, Strategy Tester docs |
| Phase 14.1 compile fix | Fix Trial/Tester execution call mismatch | Compile signature mismatch resolved | None known | Completed | `UpcomersNYSessionPropBot.mq5`, tests |
| Phase 14.2 tester diagnostics | Fix presets and add signal diagnostics | Strategy counts, reason counts, parser extraction | Use diagnostics before judging zero-trade runs | Completed | `StrategyDiagnostics.mqh`, parser, docs |
| Phase 14.3 entry intent diagnostics | Explain intents not becoming orders | Tester gate and order-attempt counters added | None known in current issue | Completed | `TesterExecution.mqh`, parser |
| Phase 14.4 tester rejection diagnosis | Fix all Strategy Tester OrderSend rejections | Request normalization, filling-mode selection, detailed retcode logging | Keep tester-only | Completed | `TesterExecution.mqh`, parser |
| Phase 14.5 result packaging | Package and compare Strategy Tester results without screenshots | Parser metrics, collector folder support, comparator CLI, docs/tests | User should export current ORB/VWAP reports and package them | Completed | `scripts/compare_strategy_tester_runs.py`, `docs/strategy_tester_result_packaging.md` |

## 6. Current State

What works:

- Native MQL5 EA source tree exists.
- MetaEditor compile wrapper works when MetaEditor is available.
- MQL5 source scan passes with exactly two allowed order-call locations.
- Strategy modules produce monitor-only signal/intention records.
- Trial micro-execution is isolated and disabled by default.
- Strategy Tester simulated execution works in tester runtime.
- Strategy Tester parser can extract diagnostics and performance fields.
- Strategy Tester collector can package export folders locally.
- Strategy Tester comparator can create Markdown/JSON comparison tables.
- Settings generator can create monitor-only, Trial micro-execution, ORB tester,
  and VWAP tester presets.
- Security/scanner/audit tooling is local-only and does not upload source.

What is partially implemented:

- Risk management has strict input gates and some live/tester order request
  checks, but full real account drawdown/equity integration for protected
  stages is not complete.
- Daily and overall loss guards exist as configuration and rule guards, but
  current Upcomers reset timezone and Dynamic Risk Shield details are unresolved.
- News filtering is a placeholder.
- Trial evidence workflow exists, but formal evidence is incomplete because raw
  logs and required notes were not collected for the first smoke.
- Strategy Tester evidence workflow exists, but latest manual ORB/VWAP results
  need to be exported and collected through it.

What is broken or untrusted:

- No known current compile-breaking MQL5 errors after Phase 14.5.
- No known current source-scan failures after Phase 14.5.
- Strategy profitability is unproven and should not be trusted.
- The latest user-reported ORB/VWAP tester results were slightly negative.
- MT5 Strategy Tester visual input refresh can be misleading after loading a
  `.set`; inspect the `.set` and summary JSON directly.
- Formal Trial evidence is not complete.
- Surge 2 Step and Vanguard rules are not encoded.

Readiness:

- Ready for local source scans: yes.
- Ready for MetaEditor compile checks: yes.
- Ready for Strategy Tester research: yes, with tester-only presets and no
  protected account use.
- Ready for Trial Risk-Free monitor-only attachment: only after manual checklist
  checks and safe settings review.
- Ready for Trial micro-execution: not as a default next step; only after source
  scan, compile, broker-time validation, manual checklist, and explicit human
  decision. Stop after first accepted trade or first broker rejection.
- Ready for Surge 2 Step, Vanguard, Challenge, Verification, Funded, or live
  prop-firm use: no.

## 7. Strategy Logic

All strategies are intended to evaluate closed bars only. Strategy decisions are
not trades. They become monitor-only records unless Strategy Tester simulated
execution is active or the Trial Risk-Free micro-execution path is explicitly
armed.

Shared signal states include:

- `WAIT`
- `SETUP_FORMING`
- `SIGNAL_SKIP_SESSION`
- `SIGNAL_SKIP_SPREAD`
- `SIGNAL_ENTER_LONG_INTENT`
- `SIGNAL_ENTER_SHORT_INTENT`
- `SIGNAL_EXIT_INTENT`

The main strategy contract is in
`mql5/Include/UpcomersNYSessionPropBot/StrategyBase.mqh`.

### Opening Range Breakout

File: `mql5/Include/UpcomersNYSessionPropBot/OpeningRangeBreakout.mqh`

Purpose: low-frequency New York session breakout/retest logic.

Entry logic:

- Builds the opening range from closed M1 bars.
- Converts `OpeningRangeMinutes` to M1 bars.
- Defaults to break-then-retest behavior, not first-touch breakout.
- Long intent requires a closed-bar break above the opening range high plus
  buffer, a retest that holds the broken level, and confirmation back in the
  breakout direction.
- Short intent is symmetrical below the range low.

Filters and invalidation:

- Session gate upstream.
- Spread gate upstream.
- Blocks unknown or excessive spread.
- Blocks too-small or too-large opening ranges relative to volatility.
- Blocks late signals.
- Uses cooldown and per-session signal cap.
- Suppresses duplicate setup signals.

Stops/takes:

- Suggested SL is based on retest/breakout structure plus buffer.
- Suggested TP is R-multiple based. Current default ORB TP multiple is
  `OpeningRangeTakeProfitR=2.0`.

Known weaknesses:

- Recent tester results over 2026-04-01 to 2026-06-01 were slightly negative.
- ORB parameters have not been optimized and should not be optimized yet.
- Broker time/session accuracy can materially change results.

### VWAP Trend Continuation

File: `mql5/Include/UpcomersNYSessionPropBot/VWAPTrendContinuation.mqh`

Purpose: continuation entries after impulse, pullback, and rejection around
session VWAP.

Entry logic:

- Uses closed M5 bars in tester presets.
- Computes VWAP from typical price and tick volume.
- Requires directional control relative to VWAP.
- Requires VWAP slope.
- Requires impulse away from VWAP.
- Requires controlled pullback near VWAP.
- Requires rejection candle confirmation back in the trend direction.

Filters and invalidation:

- Blocks flat/choppy VWAP conditions.
- Blocks missing impulse.
- Blocks missing pullback/rejection.
- Uses cooldown and per-session signal cap.
- Uses spread/session gates upstream.

Stops/takes:

- Suggested SL is below the pullback low or VWAP buffer for longs.
- Suggested SL is above the pullback high or VWAP buffer for shorts.
- TP is suggested by strategy logic, but exit behavior is still mostly attached
  SL/TP in Trial/tester execution, not advanced management.

Known weaknesses:

- Latest user-reported tester result over 2026-04-01 to 2026-06-01 was
  approximately -7.92 USD on a 10000.00 starting balance.
- VWAP preset load in MT5 can visually show stale input values; verify the
  `.set` file and summary JSON.

### Dynamic Noise-Band Momentum plus VWAP Stop

File: `mql5/Include/UpcomersNYSessionPropBot/NoiseBandMomentum.mqh`

Purpose: engineered monitor-only momentum rule set using VWAP-centered bands.

Entry logic:

- Uses VWAP as band center.
- Band width uses ATR and standard deviation style expansion.
- Requires compression, closed-bar band break, range expansion, and normalized
  momentum.

Stops/takes:

- Suggested SL is beyond breakout bar or VWAP buffer.

Known weaknesses:

- This is a derived engineered strategy, not a known proven system.
- It needs much more Strategy Tester research before any live-chart use.

### London/New York Overlap Momentum

File: `mql5/Include/UpcomersNYSessionPropBot/LondonNYOverlapMomentum.mqh`

Purpose: FX/gold-focused overlap momentum strategy.

Entry logic:

- Reference range: 07:00-08:00 New York.
- Trading window: 08:00-12:00 New York.
- Requires range break and trend alignment.
- Prefers break/retest confirmation.

Filters:

- Blocks U.S. index CFDs by default unless a later approved phase adds an
  explicit opt-in.
- Hard-blocks late overlap signals near 11:55 New York.

Known weaknesses:

- Requires broker-time/session verification.
- Not enough tester evidence yet.

### Volume/Volatility Expansion

File: `mql5/Include/UpcomersNYSessionPropBot/VolatilityExpansion.mqh`

Purpose: expansion from a contraction/setup box.

Entry logic:

- Builds setup box from recent closed bars.
- Requires prior contraction.
- Requires break outside setup box.
- Requires range expansion relative to ATR.
- Requires volume expansion relative to median volume.
- Uses real volume when available and tick volume fallback otherwise.

Known weaknesses:

- Broker volume behavior may vary.
- Needs more tester research.

### Exit Logic

Exit logic is not advanced yet.

Implemented/available:

- Entry intents must include stop-loss and take-profit before Trial/tester
  execution can send an order.
- Trial/tester order requests attach SL and TP.
- `MinHoldSeconds=180` exists as a guard against sub-2-minute scalping.
- Strategy Tester parser flags sub-180-second closes if report/log data exposes
  hold durations.

Not implemented:

- No trailing stop.
- No breakeven.
- No pending orders.
- No scaling.
- No retry loop.
- No portfolio-level live exit orchestration.
- No protected-stage account-equity exit logic.

## 8. Risk Management and Prop Firm Protection

Risk and protection defaults are intentionally conservative.

Implemented protections:

- `EnableTrading=false` default.
- `EnableTrialExecution=false` default.
- `StrategyTesterExecutionMode=false` default.
- `EnablePropChallengeMode=false` default.
- `AccountStage=MonitorOnly` default.
- `StopLossRequired=true`.
- `MinHoldSeconds=180`.
- `RiskPerTradePct=0.25`.
- `MaxRiskPerTradePct=0.50`.
- `MaxDailyLossSoftPct=2.5`.
- `MaxDailyLossHardPct=3.0`.
- `MaxOverallLossSoftPct=5.0`.
- `MaxOverallLossHardPct=6.0`.
- Daily hard loss setting must stay below 4 percent.
- Overall hard loss setting must stay below 7 percent.
- `MaxTradesPerDay=1` for Trial/tester paths.
- `MaxOpenPositionsTotal=1`.
- `MaxOpenPositionsPerSymbol=1`.
- `MaxServerMessagesPerDay=500`.
- `AllowedSymbols=EURUSD`.
- `UseSpreadFilter=true`.
- `SpreadUnknownBlocksTrading=true`.
- Prohibited flags default false:
  `AllowGrid`, `AllowMartingale`, `AllowAveragingDown`, `AllowHFT`,
  `AllowArbitrage`, `AllowCopyTrading`, `AllowScalpingUnder2Minutes`.
- Source scanner fails order calls outside `TrialExecution.mqh` and
  `TesterExecution.mqh`.
- Source scanner fails prohibited strategy terms/patterns except disabled
  safety inputs.
- Challenge/Verification/Funded metadata gates require trial evidence,
  source scan pass, compile pass, audit package ID, human approval ID, reset
  timezone confirmation, and Dynamic Risk Shield confirmation.

Lot sizing:

- Trial execution uses broker minimum/step metadata and selects a minimum safe
  volume rather than trying to maximize risk budget.
- Tester execution normalizes volume to broker min/step.
- Both paths log volume metadata.
- This is conservative but still not fully equivalent to production-grade
  position sizing across all brokers.

Stop-loss/take-profit:

- Entry intents without both SL and TP are blocked.
- SL/TP geometry must make sense for long/short direction.
- Stops are checked against broker `SYMBOL_TRADE_STOPS_LEVEL` when available.
- Tester requests normalize price, SL, and TP to symbol digits.

Daily/overall loss:

- Config guards exist and are stricter than the typical 4 percent daily and
  7 percent overall caps discussed in the project.
- `PropDayResetTimezone=UNCONFIRMED_CONSERVATIVE` by default.
- Daily reset timezone must be confirmed from current Upcomers rules before
  protected-stage use.
- Exact Dynamic Risk Shield calculation must be verified before Challenge,
  Verification, or Funded presets are enabled.

Partial/missing protections:

- No complete live equity/balance integration for protected stages.
- No formal encoded Surge 2 Step rules.
- No formal encoded Vanguard rules.
- News filter is a placeholder.
- Historical broker server time offset changes are not inferred.
- Broker-specific slippage/requote/live-vs-demo behavior is not fully modeled.
- Formal Trial evidence is incomplete.

## 9. Architecture and Code Structure

Repository-level files:

- `AGENTS.md`: hard safety instructions for agents. Read first.
- `README.md`: project overview and current native MQL5 EA direction.
- `config/default.yaml`: default Python/non-live config.
- `config/mt5_transformation.yaml`: MT5 direction/config flags, all disabled
  or unresolved by default.
- `.gitignore`: excludes generated caches/artifacts.

MQL5 source:

- `mql5/Experts/UpcomersNYSessionPropBot/UpcomersNYSessionPropBot.mq5`:
  EA entrypoint. Defines inputs, builds `SUpcomersConfig`, validates startup
  gates, runs `OnInit`, `OnTick`, `OnTimer`, strategy selection, Trial
  execution handoff, tester execution handoff, and shutdown summaries.
- `mql5/Include/UpcomersNYSessionPropBot/Config.mqh`:
  enums, config struct, account/stage helpers, metadata checks, Trial and
  tester config validation helpers.
- `Logger.mqh`: EA logging helper.
- `RiskManager.mqh`: risk guard stubs and hypothetical intent checks.
- `PropFirmRules.mqh`: prop-stage guard logic and unresolved-rule blockers.
- `SessionManager.mqh`: broker server time to UTC to New York conversion,
  session windows.
- `SymbolManager.mqh`: symbol and spread metadata checks.
- `StrategyBase.mqh`: signal/result contract and shared strategy decision data.
- `OpeningRangeBreakout.mqh`, `VWAPTrendContinuation.mqh`,
  `NoiseBandMomentum.mqh`, `LondonNYOverlapMomentum.mqh`,
  `VolatilityExpansion.mqh`: strategy signal modules.
- `TradeManager.mqh`: monitor-only no-trade refusal layer.
- `TrialExecution.mqh`: isolated Trial Risk-Free live micro-execution module.
- `TesterExecution.mqh`: isolated Strategy Tester simulated execution module.
- `StateManager.mqh`: timer/tick counters, closed-bar throttle, min-hold state.
- `MessageCounter.mqh`: monitor evaluations, trade intents, refused actions,
  and actual server-message counters.
- `AuditLogger.mqh`: local EA audit logging.
- `StrategyDiagnostics.mqh`: Strategy Tester diagnostic counters and summary.
- `NewsFilterPlaceholder.mqh`: placeholder filter. Not a real news integration.

Python support:

- `scripts/run_mql5_source_scan.py`: local static source scan.
- `scripts/compile_mql5_ea.py`: MetaEditor compile wrapper. Does not log into
  MT5 or use credentials.
- `scripts/generate_ea_settings.py`: generates safe `.set`, `.summary.json`,
  and `.summary.md` files.
- `scripts/inspect_ea_settings.py`: inspects generated `.set` files.
- `scripts/parse_strategy_tester_report.py`: parses tester reports/logs.
- `scripts/collect_strategy_tester_evidence.py`: copies/redacts tester artifacts
  into a local evidence package.
- `scripts/compare_strategy_tester_runs.py`: compares parsed tester runs.
- `scripts/export_prop_compliance_report.py`: creates compliance report.
- `scripts/export_ea_audit_package.py`: packages audit evidence.
- `scripts/collect_trial_observation_evidence.py` and
  `scripts/verify_trial_observation_package.py`: Trial evidence workflows.
- `src/trading_bot/mql5/`: Python models/settings/source scanning helpers.
- `src/trading_bot/mt5/demo_execution.py`: legacy Python MT5 execution module,
  quarantined as non-prop-compatible.

Docs:

- `docs/mql5_ea_architecture.md`
- `docs/ea_user_manual.md`
- `docs/ea_settings_reference.md`
- `docs/mql5_source_scanning.md`
- `docs/strategy_tester_workflow.md`
- `docs/strategy_tester_result_packaging.md`
- `docs/trial_micro_execution_checklist.md`
- `docs/trial_observation_evidence.md`
- `docs/troubleshooting.md`
- `docs/known_limitations.md`

Tests:

- `tests/test_mql5_source_scanner.py`
- `tests/test_mql5_ea_skeleton.py`
- `tests/test_mql5_phase13_1_safety_checkpoint.py`
- `tests/test_mql5_phase13_3_startup_diagnostics.py`
- `tests/test_mql5_phase14_strategy_tester_execution.py`
- `tests/test_mql5_phase14_2_strategy_diagnostics.py`
- `tests/test_mql5_phase14_3_tester_execution_diagnostics.py`
- `tests/test_mql5_phase14_4_tester_order_rejections.py`
- `tests/test_mql5_phase14_5_strategy_tester_results.py`
- `tests/test_strategy_tester_workflow.py`

## 10. Important Implementation Details

MetaTrader 5 integration:

- The EA is native MQL5.
- MetaEditor compile is run through `scripts/compile_mql5_ea.py`.
- The compile wrapper writes logs under `data/processed/mql5_compile/`.
- The compile wrapper does not log into MT5 and does not use credentials.
- Common MetaEditor path detection is handled by `scripts/check_metaeditor.py`.

EA runtime flow:

1. `OnInit` loads inputs into `SUpcomersConfig`.
2. Startup config summary is logged.
3. Startup validation runs.
4. If gates fail, the EA returns `INIT_PARAMETERS_INCORRECT` and logs exact
   gate failures.
5. If safe enough, timer/evaluation begins.
6. `OnTick`/`OnTimer` pass through `StateManager.ShouldEvaluateMonitorEvent`.
7. Closed-bar throttling prevents repeated per-tick evaluation.
8. Session, symbol, spread, news placeholder, prop rules, loss/risk, and
   strategy selection run.
9. Strategy decision is logged.
10. Default `TradeManager` refuses actionable intents.
11. If `EnableTrialExecution=true`, `TrialExecution` may process only valid
    entry intents and only after all Trial gates pass.
12. If `StrategyTesterExecutionMode=true` and MT5 reports tester runtime,
    `TesterExecution` may process valid entry intents as simulated tester
    orders.

Order execution flow:

- `OrderSend` appears only in:
  - `mql5/Include/UpcomersNYSessionPropBot/TrialExecution.mqh`
  - `mql5/Include/UpcomersNYSessionPropBot/TesterExecution.mqh`
- No `CTrade.Buy`, `CTrade.Sell`, pending-order helpers, or position-open helper
  calls should appear elsewhere.
- WAIT/SKIP/SETUP_FORMING/RETEST_FAIL/ORB_WIDTH_BLOCK must not execute.
- Only `ENTER_LONG_INTENT` or `ENTER_SHORT_INTENT` with valid SL/TP can reach
  execution modules.
- Trial execution sends one request and has no retry loop.
- Tester execution is research-only and requires tester runtime.

Python usage:

- Python creates settings, scans source, parses reports/logs, exports audit
  packages, and runs tests.
- Python must not control MT5 prop execution.
- The system `python` alias on this machine has previously been the Windows
  Store stub. Prefer a project venv or the bundled Codex Python path when
  running verification.

Logging:

- Startup summary and gate failures are important.
- `GATE_FAIL_<NAME>` indicates startup validation failure.
- `STRATEGY_DIAGNOSTICS_SUMMARY` summarizes tester signal counts.
- `TESTER_EXECUTION_SUMMARY` summarizes tester intents/orders/rejections.
- `TESTER_EXECUTION_BROKER_RESPONSE` and
  `TESTER_EXECUTION_ORDER_REJECTED` include retcodes/comments and request
  metadata.
- Routine throttle skip logs are suppressed by default with
  `LogThrottleSkips=false`.

Fragile/sensitive parts:

- `Config.mqh` gate logic is safety-critical.
- `TrialExecution.mqh` and `TesterExecution.mqh` are the only allowed order
  modules.
- `source_scan.py` and `run_mql5_source_scan.py` enforce code boundaries.
- Generated `.set` files can arm risky modes. Always inspect them.
- MT5 input-grid display may visually retain old values after loading `.set`.
  Trust the file and summary JSON, then manually verify the visible MT5 inputs.

## 11. Configuration and Parameters

Key EA inputs are defined in
`mql5/Experts/UpcomersNYSessionPropBot/UpcomersNYSessionPropBot.mq5`.

| Parameter | Controls | Safe/default | Dangerous values | Optimization? |
| --- | --- | --- | --- | --- |
| `EnableTrading` | General trading toggle | `false` | `true` outside approved Trial micro path | No |
| `EnableTrialExecution` | Trial live micro-execution toggle | `false` | `true` without all Trial gates and manual approval | No |
| `StrategyTesterExecutionMode` | Tester simulated execution | `false` | `true` on live chart should fail init | No |
| `EnablePropChallengeMode` | Protected prop challenge mode | `false` | `true` before exact rules/evidence/approval | No |
| `AccountProgram` | Program selection | `ACCOUNT_PROGRAM_TRIAL_RISK_FREE` | `Vanguard` or `Surge2Step` with active/trading mode | No |
| `AccountStage` | Stage selection | `ACCOUNT_STAGE_MONITOR_ONLY` | Challenge/Verification/Funded before metadata complete | No |
| `RequireManualConfirmationText` | Forces explicit phrase | `true` | `false` | No |
| `ManualConfirmationText` | Human arming phrase | blank by default | Incorrect phrase with trading toggles | No |
| `AccountProgramRulesReviewId` | Rule review metadata | blank for Trial/tester | Required missing for protected stages | No |
| `TrialEvidenceId` | Trial evidence metadata | blank until formal evidence | Required missing for protected stages | No |
| `SourceScanPassId` | Source scan PASS marker | required for Trial micro | blank with Trial micro | No |
| `CompilePassId` | Compile PASS marker | required for protected stages | blank for protected stages | No |
| `FinalAuditPackageId` | Audit package marker | required for protected stages | blank for protected stages | No |
| `HumanApprovalId` | Human approval metadata | required for protected stages | blank for protected stages | No |
| `PropDayResetTimezone` | Prop day reset timezone | `UNCONFIRMED_CONSERVATIVE` | assuming UTC without current rules | No |
| `PropDayResetTimezoneConfirmationId` | Reset timezone evidence | blank until confirmed | blank for protected stages | No |
| `DynamicRiskShieldConfirmationId` | Dynamic Risk Shield evidence | blank until verified | blank for protected stages | No |
| `MaxDailyLossSoftPct` | Daily soft guard | `2.5` | greater than hard guard | No |
| `MaxDailyLossHardPct` | Daily hard guard | `3.0`, must be below `4.0` | `>=4.0` | No |
| `MaxOverallLossSoftPct` | Overall soft guard | `5.0` | greater than hard guard | No |
| `MaxOverallLossHardPct` | Overall hard guard | `6.0`, must be below `7.0` | `>=7.0` | No |
| `RiskPerTradePct` | Intended risk budget | `0.25` | above `0.25` for Trial micro, above max cap | Not yet |
| `MaxRiskPerTradePct` | Absolute per-trade cap | `0.50` | above `0.50` | No |
| `MaxTradesPerDay` | Trade-intent/order cap | `1` for Trial/tester | greater than 1 in Trial micro | No |
| `MaxServerMessagesPerDay` | Server message cap | `500` | too high, above scanner/gate limit | No |
| `MinHoldSeconds` | Minimum hold guard | `180` | below `180` | No |
| `StopLossRequired` | Requires SL on intents | `true` | `false` | No |
| `MaxOpenPositionsTotal` | Total open position cap | `1` | greater than 1 in Trial micro | No |
| `MaxOpenPositionsPerSymbol` | Per-symbol cap | `1` | greater than 1 in Trial micro | No |
| `AllowedSymbols` | Symbol allowlist | `EURUSD` | adding symbols before approved phase | No |
| `TrialExecutionMagicNumber` | Trial order magic number | `26060113` | changing without audit trace | No |
| `AllowGrid` | Prohibited behavior flag | `false` | `true` | No |
| `AllowMartingale` | Prohibited behavior flag | `false` | `true` | No |
| `AllowAveragingDown` | Prohibited behavior flag | `false` | `true` | No |
| `AllowHFT` | Prohibited behavior flag | `false` | `true` | No |
| `AllowArbitrage` | Prohibited behavior flag | `false` | `true` | No |
| `AllowCopyTrading` | Prohibited behavior flag | `false` | `true` | No |
| `AllowScalpingUnder2Minutes` | Prohibited behavior flag | `false` | `true` | No |
| `StrategySelection` | Strategy module | ORB default, tester presets ORB/VWAP | switching without confirming generated `.set` | Later maybe |
| `StrategyTimeframe` | Signal timeframe | source default `PERIOD_M1`, tester presets `PERIOD_M5` | mismatch with strategy assumptions | Later maybe |
| `OpeningRangeMinutes` | ORB range length | `15` | untested changes | Later maybe |
| `OpeningRangeMinRangePoints` | ORB min range | `10.0` | untested changes | Later maybe |
| `OpeningRangeTakeProfitR` | ORB TP multiple | `2.0` | optimization before stable evidence | Later maybe |
| `VWAPLookbackBars` | VWAP lookback | `30` | untested changes | Later maybe |
| `VWAPStopBufferPoints` | VWAP stop buffer | `20.0` | untested changes | Later maybe |
| `StrategySignalCooldownSeconds` | Signal cooldown | `900` | too low creates spam | Later maybe |
| `MaxSignalsPerStrategyPerSession` | Signal cap | `1` | too high before review | Later maybe |
| `BrokerTimeMode` | Broker time conversion mode | `BROKER_TIME_MANUAL_UTC_OFFSET` | assuming broker time without validation | No |
| `BrokerServerUtcOffsetMinutes` | Server UTC offset | `0` default, user used `120` in Trial settings | wrong offset corrupts sessions | No |
| `RequireBrokerTimeValidation` | Requires offset note | `true` | `false` | No |
| `BrokerTimeValidationNote` | Manual offset evidence | required for Trial micro | blank with Trial micro | No |
| `MaxSpreadPoints` | Spread gate | `30` | too high or disabled spread gate | Maybe later |
| `UseSpreadFilter` | Enables spread gate | `true` | `false` | No |
| `SpreadUnknownBlocksTrading` | Unknown spread handling | `true` | `false` | No |
| `EvaluationMode` | Throttle mode | `EVALUATION_ON_NEW_CLOSED_BAR` | per-tick behavior before review | No |
| `MinEvaluationSeconds` | Evaluation throttle | `60` | too low creates noisy/too frequent behavior | No |
| `LogThrottleSkips` | Routine throttle logging | `false` | verbose during long observation | No |

Generated presets:

- `trial-monitor-only`: safe monitor-only Trial settings.
- `trial-risk-free-eurusd-micro-execution`: arms Trial micro-execution only if
  `SourceScanPassId` and broker-time validation note are provided.
- `strategy-tester-eurusd-m5-orb`: tester-only ORB simulated execution.
- `strategy-tester-eurusd-m5-vwap`: tester-only VWAP simulated execution.

## 12. Testing Status

Automated verification from recent phases:

- Phase 14.5 focused tests passed: `11 passed`.
- `ruff check .` passed after Phase 14.5.
- `scripts/run_mql5_source_scan.py --json` passed after Phase 14.5.
- `scripts/compile_mql5_ea.py --json` passed after Phase 14.5.
- Latest known compile log from prior work:
  `data/processed/mql5_compile/compile_20260602T200319Z.log`.
- Order-call grep showed only:
  - `mql5/Include/UpcomersNYSessionPropBot/TesterExecution.mqh`
  - `mql5/Include/UpcomersNYSessionPropBot/TrialExecution.mqh`

Manual/observed tests:

- Trial monitor-only smoke: about 27 minutes on EURUSD M5, zero orders, zero
  positions, no Experts/Journal errors, monitor and strategy logs present.
  Evidence status: smoke-only/informal because raw logs and required notes were
  missing.
- Trial micro-execution armed observation: about 2 hours on EURUSD M5, no
  accepted trade, no broker rejection, no repeated order attempts. The EA stayed
  armed waiting for entry intents.
- Strategy Tester VWAP EURUSD M5 2026-04-01 to 2026-06-01: user-reported
  40 entry intents received, 40 attempted, 40 sent successfully, 0 rejected,
  final balance 9992.08 from 10000.00.
- Strategy Tester ORB EURUSD M5 2026-04-01 to 2026-06-01: user-reported
  43 entry intents received, 42 attempted, 42 sent successfully, 0 rejected,
  final balance 9996.37 from 10000.00.

Testing gaps:

- Latest ORB/VWAP Strategy Tester raw reports/logs still need to be exported
  and packaged through Phase 14.5 tooling.
- Formal Trial observation evidence is incomplete.
- No protected-account test is approved.
- No Surge 2 Step rules encoded or tested.
- No Vanguard rules encoded or tested.
- No current Upcomers rule confirmation for daily reset timezone.
- No current Upcomers Dynamic Risk Shield calculation encoded.
- No statistically meaningful backtest matrix yet.
- No optimization should occur yet.

## 13. Known Issues and Bugs

### Critical

1. Protected account rules are incomplete.
   - Description: Surge 2 Step and Vanguard exact rules are not encoded.
   - Likely cause: rules have not been reviewed and formalized.
   - Affected files: `Config.mqh`, `PropFirmRules.mqh`,
     `config/mt5_transformation.yaml`, docs.
   - Suggested fix: review current Upcomers rules, encode program-specific
     constraints, add tests and docs.
   - Blocks live trading: yes.

2. Daily reset timezone and Dynamic Risk Shield are unresolved.
   - Description: `PropDayResetTimezone` defaults to
     `UNCONFIRMED_CONSERVATIVE`; Dynamic Risk Shield calculation is unverified.
   - Likely cause: current Upcomers rules not confirmed.
   - Affected files: `PropFirmRules.mqh`, `Config.mqh`,
     `config/mt5_transformation.yaml`, docs.
   - Suggested fix: confirm rules from current Upcomers materials, add evidence
     IDs and tests.
   - Blocks Challenge/Verification/Funded/protected use: yes.

3. Formal Trial evidence is incomplete.
   - Description: first Trial monitor-only run is smoke-only/informal.
   - Likely cause: raw logs and required notes were missing.
   - Affected files: `scripts/verify_trial_observation_package.py`,
     `docs/trial_observation_evidence.md`.
   - Suggested fix: collect raw Experts/Journal logs, broker-time note,
     symbol-session note, no-order/no-position note, safe settings, source
     scan, compile log.
   - Blocks protected account approval: yes.

### High

1. Strategy profitability is unproven and currently not encouraging.
   - Description: latest user-reported ORB/VWAP tester results were negative.
   - Likely cause: strategy rules may be too strict, weak, or not tuned to the
     tested period.
   - Affected files: strategy modules and tester evidence tooling.
   - Suggested fix: package current tester results, run a small non-optimized
     matrix, analyze diagnostics before changing rules.
   - Blocks live trading: yes.

2. Broker-time/session correctness must be manually verified.
   - Description: wrong `BrokerServerUtcOffsetMinutes` can shift sessions.
   - Likely cause: broker server time differs from UTC/New York and may change.
   - Affected files: `SessionManager.mqh`, settings, docs.
   - Suggested fix: verify current broker server offset and symbol sessions in
     MT5; record notes.
   - Blocks reliable Trial testing: yes.

3. News filter is placeholder only.
   - Description: no real economic-news blocking.
   - Likely cause: Phase scope did not add news integration.
   - Affected file: `NewsFilterPlaceholder.mqh`.
   - Suggested fix: add reviewed, local-safe news calendar workflow later.
   - Blocks high-confidence live use: yes.

### Medium

1. MT5 input grid may visually retain stale `.set` values.
   - Description: user saw VWAP `.set` file correct but MT5 display sometimes
     retained ORB until manually changed.
   - Likely cause: MT5 UI refresh/load behavior.
   - Affected files: docs and operator workflow.
   - Suggested fix: inspect `.set` and `.summary.json`; manually verify MT5
     visible inputs.
   - Blocks live trading: indirectly, because wrong strategy may run.

2. Risk manager is still partly a monitor/tester guard layer.
   - Description: full live equity, floating P/L, daily reset, and account
     protection integration for protected stages is not complete.
   - Likely cause: phases have prioritized safety gates and tester research.
   - Affected files: `RiskManager.mqh`, `PropFirmRules.mqh`,
     `TrialExecution.mqh`.
   - Suggested fix: implement only after rules and evidence are complete.
   - Blocks protected live use: yes.

3. Strategy Tester results are not yet packaged.
   - Description: Phase 14.5 tooling exists, but current ORB/VWAP manual
     results need raw exports.
   - Likely cause: tooling was just added.
   - Affected files: `scripts/collect_strategy_tester_evidence.py`,
     `scripts/compare_strategy_tester_runs.py`.
   - Suggested fix: export report/log folders and run collector/comparator.
   - Blocks research comparison: yes, but not source development.

### Low

1. Some docs still reflect earlier phase wording.
   - Description: a few docs may say "Phase 9" or "Phase 13" in places where
     current state is post-Phase 14.5.
   - Likely cause: phased development history.
   - Affected files: docs.
   - Suggested fix: only update when it clarifies safety/current status.
   - Blocks live trading: no.

2. Generated artifacts can clutter local workspace.
   - Description: pytest/ruff caches, compile logs, tester evidence, and raw
     data artifacts accumulate.
   - Likely cause: normal verification.
   - Affected files: `.gitignore`, `scripts/clean_artifacts.py`, `data/`.
   - Suggested fix: run cleanup script carefully; never delete source/docs/tests.
   - Blocks live trading: no.

## 14. Abandoned or Rejected Approaches

Python-controlled MT5 execution:

- What it was: using Python and MT5 bindings to place or manage orders.
- Why rejected: prop-compatible execution must be native MQL5 EA only; Python
  execution creates unacceptable boundary and credential risks.
- Future use: no prop-firm execution use. Python may remain read-only/support.

Binance/crypto as primary product direction:

- What it was: original public-data crypto research and backtesting framework.
- Why postponed: current product direction is Upcomers native MT5 EA.
- Future use: still valuable for research, validation, reports, artifacts, and
  safety patterns.

Monitor-only EA as "approval":

- What it was: treating Trial monitor success as broader approval.
- Why rejected: Trial Risk-Free is only the first MT5 platform testing
  environment; it does not approve Surge, Vanguard, or funded use.
- Future use: monitor-only evidence remains one input, not approval.

Screenshots as required formal evidence:

- What it was: formal Trial evidence could have required screenshots.
- Why changed: user does not want screenshots; raw logs and notes are more
  useful.
- Future use: screenshots optional; raw logs and required notes are mandatory
  for formal Trial evidence.

Strategy Tester monitor-only only:

- What it was: tester workflow initially expected zero trades/deals.
- Why changed: strategy behavior needed historical simulated execution.
- Future use: monitor-only tester mode still useful, but simulated tester mode
  now exists for research.

Optimization:

- What it was: possible parameter search after tester execution worked.
- Why postponed: project is not ready; first need repeatable packaging,
  diagnostics, and small matrix comparison.
- Future use: only after evidence workflow, data windows, and safety review are
  stable.

Grid, martingale, averaging down, HFT, arbitrage, copy trading, sub-2-minute
scalping:

- What they were: prohibited strategy categories.
- Why rejected: incompatible with the safety model and prop-firm protection.
- Future use: none.

## 15. Current TODO List

Immediate next steps:

- Export current ORB and VWAP MT5 Strategy Tester reports/logs into folders.
- Keep each folder with its `.set` file and generated summary JSON if
  available.
- Run `scripts/collect_strategy_tester_evidence.py --simulated-execution` for
  each run.
- Run `scripts/compare_strategy_tester_runs.py` to create Markdown/JSON
  comparison.
- Review diagnostics: entry intents, orders attempted, orders sent, trades,
  net profit, drawdown, profit factor, warnings.
- Do not change strategy rules until current evidence is packaged.

Before more Trial testing:

- Run source scan and compile.
- Verify broker server UTC offset manually.
- Verify symbol sessions manually.
- Verify spread/stops/min lot/volume step/tick value/tick size for EURUSD.
- Use only Trial Risk-Free account.
- Confirm `EnableTrading=false` for monitor-only or strict Trial micro gates for
  one-shot micro-execution.
- Save raw Experts/Journal logs.
- Save settings.
- Add broker-time note, symbol-session note, and no-order/no-position note for
  formal evidence.

Before prop-firm live/protected use:

- Review current Upcomers rules.
- Encode Surge 2 Step rules.
- Encode Vanguard rules.
- Confirm daily reset timezone.
- Verify Dynamic Risk Shield calculation.
- Collect formal Trial observation evidence.
- Produce source scan PASS artifact.
- Produce compile PASS artifact.
- Produce Strategy Tester evidence.
- Produce compliance report.
- Produce final audit package.
- Obtain explicit human approval metadata.
- Keep Challenge/Verification/Funded presets disabled until all blockers clear.

Later improvements:

- Add real news filter workflow.
- Improve risk/equity/drawdown integration for any future protected-stage design.
- Expand Strategy Tester matrix only after current workflow is repeatable.
- Consider carefully reviewed strategy improvements after diagnostics show why
  results are weak.
- Add more robust parsing for additional MT5 report formats if needed.
- Add operator summary dashboard for evidence packages if useful.

## 16. Safety Notes

What could cause account failure:

- Running the EA on Surge 2 Step, Vanguard, Challenge, Verification, Funded, or
  live-money account before explicit approval.
- Enabling `EnableTrading=true` or `EnableTrialExecution=true` on the wrong
  account.
- Loading a stale/wrong `.set` file.
- Trusting the MT5 input grid without checking the actual `.set`.
- Using wrong broker server UTC offset.
- Misidentifying symbol sessions.
- Disabling spread filter or allowing unknown spread.
- Increasing trades/day, positions, risk per trade, or server messages.
- Adding prohibited behavior such as grid, martingale, averaging down, HFT,
  arbitrage, copy trading, or sub-2-minute scalping.
- Assuming Strategy Tester profitability equals live performance.
- Assuming Trial smoke evidence equals prop approval.
- Assuming daily reset timezone is UTC without verification.
- Ignoring Dynamic Risk Shield uncertainty.

Manual review required:

- Current Upcomers rule review.
- Surge 2 Step exact rules.
- Vanguard exact rules.
- Broker server time and sessions.
- Any `.set` file that enables execution.
- Any change to `TrialExecution.mqh` or `TesterExecution.mqh`.
- Any source scanner allowlist change.
- Any strategy rule change after tester results.

Parts not yet trusted:

- Profitability.
- Protected-stage readiness.
- Full drawdown/equity protection.
- News filtering.
- Broker-specific behavior outside observed EURUSD M5 tests.
- Formal Trial readiness without raw evidence.

## 17. Recommended Next Plan

The next assistant should proceed conservatively:

1. Read `AGENTS.md`, this file, `README.md`, and
   `docs/strategy_tester_workflow.md`.

2. Do not edit MQL5 strategy or execution logic at first.

3. Ask the user for the raw exported MT5 Strategy Tester folders for the latest
   ORB and VWAP runs, or tell the user how to export them if they are not in the
   workspace.

4. For each tester run, collect evidence:

   ```powershell
   python scripts/collect_strategy_tester_evidence.py ^
     --run-id tester_eurusd_m5_orb_20260401_20260601 ^
     --tester-artifacts path\to\orb_export_folder ^
     --simulated-execution ^
     --json
   ```

   ```powershell
   python scripts/collect_strategy_tester_evidence.py ^
     --run-id tester_eurusd_m5_vwap_20260401_20260601 ^
     --tester-artifacts path\to\vwap_export_folder ^
     --simulated-execution ^
     --json
   ```

5. Compare runs:

   ```powershell
   python scripts/compare_strategy_tester_runs.py ^
     data\processed\strategy_tester_evidence\tester_eurusd_m5_orb_20260401_20260601 ^
     data\processed\strategy_tester_evidence\tester_eurusd_m5_vwap_20260401_20260601 ^
     --output-md data\processed\strategy_tester_evidence\eurusd_m5_orb_vwap_compare.md ^
     --output-json data\processed\strategy_tester_evidence\eurusd_m5_orb_vwap_compare.json
   ```

6. Review parser warnings and diagnostic summaries. Determine whether results
   are based on correct strategy selection, correct symbol/timeframe, and
   expected tester execution mode.

7. Run quota-conscious verification:

   ```powershell
   python -m pytest tests/test_mql5_phase14_5_strategy_tester_results.py tests/test_strategy_tester_workflow.py
   python -m ruff check .
   python scripts/run_mql5_source_scan.py --json
   python scripts/compile_mql5_ea.py --json
   rg -n "OrderSend|CTrade|\.Buy\(|\.Sell\(|PositionOpen|BuyLimit|SellLimit|BuyStop|SellStop" mql5 src/trading_bot/mql5
   ```

8. Only after evidence is packaged, decide whether the next phase should be:
   - more Strategy Tester evidence packaging,
   - a small fixed-parameter matrix,
   - strategy diagnostics review,
   - or documentation/audit cleanup.

9. Do not optimize parameters yet.

10. Do not enable Surge, Vanguard, Challenge, Verification, Funded, or
    live-money trading.

## 18. Files to Read First

1. `AGENTS.md`
   - Contains non-negotiable agent rules.

2. `PROJECT_HANDOFF.md`
   - This document.

3. `README.md`
   - Current product direction and historical Python context.

4. `docs/mql5_ea_architecture.md`
   - Native EA architecture, runtime flow, and safety boundaries.

5. `docs/ea_user_manual.md`
   - Safe/default inputs and operator-facing behavior.

6. `docs/ea_settings_reference.md`
   - Parameters, metadata gates, and presets.

7. `docs/mql5_source_scanning.md`
   - Static scanner policy and allowed order-call locations.

8. `docs/strategy_tester_workflow.md`
   - How to run and interpret tester research safely.

9. `docs/strategy_tester_result_packaging.md`
   - Phase 14.5 packaging/comparison workflow.

10. `docs/trial_micro_execution_checklist.md`
    - Manual checklist before any Trial micro-execution consideration.

11. `docs/troubleshooting.md`
    - MT5 init code 32767 and gate-failure interpretation.

12. `mql5/Experts/UpcomersNYSessionPropBot/UpcomersNYSessionPropBot.mq5`
    - EA entrypoint and inputs.

13. `mql5/Include/UpcomersNYSessionPropBot/Config.mqh`
    - Config, enums, gates, and protected-stage metadata logic.

14. `mql5/Include/UpcomersNYSessionPropBot/TrialExecution.mqh`
    - Only Trial Risk-Free live micro-execution order path.

15. `mql5/Include/UpcomersNYSessionPropBot/TesterExecution.mqh`
    - Only Strategy Tester simulated execution order path.

16. `scripts/generate_ea_settings.py`
    - Preset generator.

17. `scripts/parse_strategy_tester_report.py`
    - Tester report parser.

18. `scripts/collect_strategy_tester_evidence.py`
    - Tester evidence packager.

19. `scripts/compare_strategy_tester_runs.py`
    - Tester run comparator.

20. `tests/test_mql5_phase14_5_strategy_tester_results.py`
    - Tests for current result packaging behavior.

## 19. Open Questions

- What are the current exact Upcomers rules for Surge 2 Step?
- What are the current exact Upcomers rules for Vanguard?
- What timezone does Upcomers use for daily loss reset?
- What is the exact Dynamic Risk Shield calculation?
- What is the verified current broker server UTC offset?
- Are EURUSD symbol sessions verified in the user's MT5 terminal?
- Can the user provide raw MT5 Strategy Tester report/log folders for the
  latest ORB/VWAP runs?
- Should the next phase remain evidence packaging, or begin a small fixed
  Strategy Tester matrix?
- Should formal Trial monitor-only evidence be collected before any further
  Trial micro-execution?
- Are there any broker-specific stop-level, freeze-level, min-lot, volume-step,
  or filling-mode changes since the last Strategy Tester run?

## 20. Final Handoff Summary

This is a safety-first Upcomers MT5 trading-bot project whose final prop-firm
execution direction is a native MQL5 Expert Advisor. Python is support-only.

Current phase: post-Phase 14.5. Strategy Tester simulated execution works and
result packaging/comparison tooling now exists. The next best action is to
export, collect, parse, and compare current ORB/VWAP Strategy Tester runs as
research-only evidence.

Biggest risks:

- Accidentally treating research/tester output as live trading approval.
- Running on Surge 2 Step, Vanguard, Challenge, Verification, Funded, or
  live-money accounts before rule review and approval.
- Misconfiguring `.set` files or trusting stale MT5 input display.
- Wrong broker-time/session assumptions.
- Unresolved daily reset timezone and Dynamic Risk Shield rules.
- Strategy performance is unproven and recent observed tester results were
  negative.

Next best action:

Package the current ORB and VWAP Strategy Tester exports with
`collect_strategy_tester_evidence.py`, compare them with
`compare_strategy_tester_runs.py`, review diagnostics, and only then decide
whether to run a small fixed-parameter Strategy Tester matrix. Do not optimize,
do not expand live execution, and do not enable protected accounts.

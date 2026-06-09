# Strategy Tester Workflow

This workflow is for local MT5 Strategy Tester evidence only. It does not trade
Trial Risk-Free, Surge 2 Step, Vanguard, Challenge, Verification, Funded, or
live accounts, and it is not a profitability claim. The first tester phase is
diagnostics, not performance proof.

## Prepare

1. Compile `UpcomersNYSessionPropBot` in MetaEditor.
2. Generate or reuse a safe Trial/MonitorOnly `.set` file.
3. Confirm the `.set` file contains:
   - `EnableTrading=false`
   - `EnableTrialExecution=false`
   - `EnablePropChallengeMode=false`
   - `AccountProgram=ACCOUNT_PROGRAM_TRIAL_RISK_FREE`
   - `AccountStage=ACCOUNT_STAGE_TRIAL` or `ACCOUNT_STAGE_MONITOR_ONLY`

Do not use prop credentials. Do not run Strategy Tester for Surge 2 Step or
Vanguard workflows.

## Run Tester

1. Open MT5.
2. Open Strategy Tester.
3. Select `UpcomersNYSessionPropBot`.
4. Choose `EURUSD` on `M5` first.
5. Use `Every tick based on real ticks` if the broker data supports it.
6. Import the safe Trial/MonitorOnly `.set` file.
7. Confirm `EnableTrading=false` inside tester inputs.
8. Confirm `EnablePropChallengeMode=false` inside tester inputs.
9. Run the test in monitor-only mode.

The EA is still monitor-only. Strategy Tester logs may show sessions, spread
checks, strategy signals, skips, and no-trade refusals. They must not be read as
proof of profitability, challenge readiness, or account approval.

## Simulated Execution Backtests

Phase 14 adds a Strategy Tester-only simulated execution mode for research
backtests. It is separate from Trial live-chart execution and must not be
attached to a live chart.

Generate the first ORB preset:

```powershell
python scripts/generate_ea_settings.py `
  --preset strategy-tester-eurusd-m5-orb `
  --json
```

Generate the VWAP preset:

```powershell
python scripts/generate_ea_settings.py `
  --preset strategy-tester-eurusd-m5-vwap `
  --json
```

The generated tester presets contain:

- `EnableTrading=false`
- `EnableTrialExecution=false`
- `StrategyTesterExecutionMode=true`
- `EnablePropChallengeMode=false`
- `AccountProgram=ACCOUNT_PROGRAM_TRIAL_RISK_FREE`
- `AccountStage=ACCOUNT_STAGE_MONITOR_ONLY`
- `AllowedSymbols=EURUSD`
- `StrategyTimeframe=PERIOD_M5`
- `MinHoldSeconds=180`
- `StopLossRequired=true`

They must also contain the intended strategy selection:

- ORB preset: `StrategySelection=STRATEGY_OPENING_RANGE_BREAKOUT`
- VWAP preset: `StrategySelection=STRATEGY_VWAP_TREND_CONTINUATION`

Before loading a preset into MT5, inspect the generated file locally:

```powershell
python scripts/inspect_ea_settings.py `
  data\processed\ea_settings\strategy_tester_eurusd_m5_vwap.set `
  --json
```

MT5 may visually retain an old Inputs-grid value after pressing Load. Treat the
`.set` file and generated `.summary.json` as the source of truth, then manually
change the visible row in MT5 if the grid did not refresh.

`StrategyTesterExecutionMode` can initialize only when the EA detects
`MQL_TESTER`. If the same preset is attached to a live chart, startup validation
must fail. Simulated tester orders are historical research events only; they do
not approve Trial, Surge 2 Step, Vanguard, Challenge, Verification, Funded, or
live-money use.

## Signal Diagnostics

During tester runs, the EA counts signal states and reason codes and emits a
final line containing `STRATEGY_DIAGNOSTICS_SUMMARY`. Review that line before
interpreting a zero-trade run.

The summary includes:

- strategy name
- total evaluations
- `ENTER_LONG_INTENT` and `ENTER_SHORT_INTENT` counts
- whether tester execution mode was active
- whether any tester orders were attempted
- reason-code counts such as `WAIT`, `SETUP_FORMING`, `ORB_WIDTH_BLOCK`,
  `RETEST_FAIL`, `ORB_SIGNAL_COOLDOWN`, `VWAP_BIAS_LONG`,
  `VWAP_BIAS_SHORT`, `VWAP_FLAT_BLOCK`, `IMPULSE_MISSING`,
  `PULLBACK_NEAR_VWAP`, and `REJECTION_CLOSE_OK`

A zero-trade tester run is meaningful only after checking the entry-intent
counts. If `enter_long=0` and `enter_short=0`, no executable entry signals were
generated. If entry-intent counts are positive but trades remain zero, execution
gates likely blocked those entries. Do not optimize yet, and do not judge a
strategy until the diagnostics explain why no trades occurred.

The tester execution layer also emits `TESTER_EXECUTION_SUMMARY`. This summary
separates entry intents that reached tester execution from requests that were
actually sent. If `enter_long` plus `enter_short` is positive but
`tester_orders_attempted=0`, inspect `top_tester_gate_failures` and the
`TESTER_GATE_FAIL_*` lines. If `tester_orders_attempted` is positive but the
tester report still shows zero trades or deals, inspect
`TESTER_EXECUTION_ORDER_REJECTED` and `TESTER_EXECUTION_BROKER_RESPONSE` lines.

## Save Evidence

After the test, save the tester report and logs locally. Useful files include:

- exported Strategy Tester HTML/XML/CSV report
- tester journal/log files
- tester inputs or `.set` file used
- source scan JSON
- compile log

Then parse and collect locally:

```powershell
python scripts/parse_strategy_tester_report.py path\to\tester_report_or_logs --json

python scripts/parse_strategy_tester_report.py `
  path\to\tester_report_or_logs `
  --simulated-execution `
  --json

python scripts/collect_strategy_tester_evidence.py ^
  --run-id tester_eurusd_m5_001 ^
  --tester-artifacts path\to\tester_report_or_logs ^
  --settings-file data\processed\ea_settings\trial_monitor_only.set ^
  --compile-log data\processed\mql5_compile\compile_TIMESTAMP.log ^
  --source-scan data\processed\mql5_source_scan\source_scan.json ^
  --json
```

For simulated Strategy Tester backtest evidence, keep the MT5 export folder
together. The collector now accepts a folder containing the exported report,
tester journal/log, the `.set` file, and generated summary JSON:

```powershell
python scripts/collect_strategy_tester_evidence.py ^
  --run-id tester_eurusd_m5_vwap_20260401_20260601 ^
  --tester-artifacts path\to\vwap_tester_export_folder ^
  --simulated-execution ^
  --json
```

This copies and redacts local files into
`data\processed\strategy_tester_evidence\<run_id>\`, writes
`parser_summary.json`, and records that the package is research-only evidence.
Screenshots are not required for this workflow. Raw exported reports and logs
are more useful than screenshots because they can be parsed and compared.

The parser expects monitor-only Strategy Tester evidence to show zero trades,
zero orders, and zero deals when those counts are present. Any trade, order, or
deal count greater than zero is a `FAIL` for monitor-only testing.

With `--simulated-execution`, tester trades are summarized as backtest research.
The parser reports trade count, profit factor, drawdown, expected payoff,
average hold time when available, and any close under 180 seconds. Missing or
unknown report formats produce `WARN`, not a false pass.

The parser also extracts `STRATEGY_DIAGNOSTICS_SUMMARY` lines and reports
whether a zero-trade run produced no executable entry signals or whether entry
signals were blocked by execution gates. If a VWAP-labeled preset or report
shows `StrategySelection=STRATEGY_OPENING_RANGE_BREAKOUT`, parsing fails so the
preset mismatch is caught before another manual tester run.

Strategy Tester evidence is separate from formal Trial observation evidence.
Formal Trial evidence may remain skipped or incomplete. Neither Strategy Tester
evidence nor Trial smoke evidence approves Surge 2 Step, Vanguard, Challenge,
Verification, Funded, live use, or trading.
Strategy Tester evidence does not approve any account use.

## Compare ORB vs VWAP

See also `docs/strategy_tester_result_packaging.md` for the shorter packaging
checklist.

After collecting ORB and VWAP evidence folders, compare them locally:

```powershell
python scripts/compare_strategy_tester_runs.py ^
  data\processed\strategy_tester_evidence\tester_eurusd_m5_orb_20260401_20260601 ^
  data\processed\strategy_tester_evidence\tester_eurusd_m5_vwap_20260401_20260601 ^
  --output-md data\processed\strategy_tester_evidence\eurusd_m5_orb_vwap_compare.md ^
  --output-json data\processed\strategy_tester_evidence\eurusd_m5_orb_vwap_compare.json
```

The comparison table includes symbol, timeframe, strategy, date range, entry
intents, orders attempted, orders sent, trades/deals, net profit, return
percent, max drawdown, profit factor, and parser warnings. Treat the table as a
small research matrix, not optimization and not prop approval. For the next
manual matrix, keep it small: `EURUSD M5`, one recent one-month window, one
two-month window, ORB preset, and VWAP preset. Do not add symbols or optimize
inputs until the basic report flow is repeatable.

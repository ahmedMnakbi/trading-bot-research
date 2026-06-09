# Trial Monitor-Only Runbook

This runbook is for the Trial Risk-Free account only. Do not attach the EA to Surge 2 Step or Vanguard. Phase 10 does not allow trading.

## Prepare

1. Generate safe settings:

```powershell
python scripts/generate_ea_settings.py --account-program TrialRiskFree --stage Trial
```

2. Run source scan and compile:

```powershell
python scripts/run_mql5_source_scan.py --json
python scripts/compile_mql5_ea.py --json
```

3. Complete broker time verification in [broker_time_verification.md](broker_time_verification.md).
4. Complete symbol session verification in [symbol_session_verification.md](symbol_session_verification.md).
5. Create formal evidence note templates:

```powershell
python scripts/create_trial_observation_notes.py --run-id RUN_ID
```

## Attach To One Chart

1. Confirm the MT5 account is Trial Risk-Free.
2. Open one low-risk chart first.
3. Attach `UpcomersNYSessionPropBot`.
4. Import the safe Trial/MonitorOnly `.set` file.
5. Verify `EnableTrading=false`.
6. Verify `EnablePropChallengeMode=false`.
7. Verify `AccountProgram=TrialRiskFree`.
8. Verify `AccountStage=Trial` or `MonitorOnly`.
9. Verify `ManualConfirmationText` is not enabling trading.
10. Verify `BrokerServerUtcOffsetMinutes` matches the broker-time checklist.
11. Verify `LogThrottleSkips=false` unless you are debugging throttling itself.
12. Verify logs show monitor-only and no-trade/refusal-only behavior.

If MT5 requires Algo Trading for EA timers/logging, enable it only after verifying the above inputs. Trading remains blocked by `EnableTrading=false` and the no-trade `TradeManager`.

## Observe

Observe for a short fixed window first, such as 15-30 minutes. Watch the Experts and Journal logs for:

- monitor-only startup
- broker/server/UTC/New York timestamp lines
- session gate results
- spread gate results
- once-per-evaluation monitor summaries
- strategy `WAIT`, `SETUP_FORMING`, `SKIP_*`, or monitor-only intent records
- no order placement, no positions opened, no Trial trades

Routine throttle-skip lines such as `THROTTLE_MIN_SECONDS` are suppressed by
default with `LogThrottleSkips=false`. The throttle still runs and still blocks
repeated per-tick evaluation between accepted monitor evaluations. Enable the
input only for short debugging windows if throttle behavior itself needs review.

## Emergency Stop

If anything unexpected appears:

1. Remove the EA from the chart.
2. Disable Algo Trading.
3. Close MT5 if needed.
4. Save raw Experts/Journal logs for review.
5. Do not attach to any other account.

## Collect Evidence

After observation, copy raw MT5 Experts/Journal logs or raw MT5 log files
unchanged into a local folder. Edited or cleaned log excerpts are acceptable
only for smoke/informal review, not formal evidence. Screenshots are optional
for now.

Fill in the generated notes:

- `data\manual_evidence\RUN_ID\broker_time_note.txt`
- `data\manual_evidence\RUN_ID\symbol_session_note.txt`
- `data\manual_evidence\RUN_ID\no_order_no_position_note.txt`

Then collect logs and manual notes with:

```powershell
python scripts/collect_trial_observation_evidence.py ^
  --evidence-kind formal_trial_observation ^
  --run-id RUN_ID ^
  --ea-logs path\to\logs ^
  --settings-file data\processed\ea_settings\trial_monitor_only.set ^
  --compile-log path\to\compile.log ^
  --source-scan path\to\source_scan.json ^
  --broker-time-note data\manual_evidence\RUN_ID\broker_time_note.txt ^
  --symbol-session-checklist data\manual_evidence\RUN_ID\symbol_session_note.txt ^
  --no-trial-trades-note data\manual_evidence\RUN_ID\no_order_no_position_note.txt
```

Do not include account passwords, investor passwords, API keys, or prop
credentials in notes or log folders. Screenshots can be added later with
`--screenshots-dir`, but they are not required for the formal package.

Trial success is not prop challenge approval. Strategy Tester evidence, Final Audit Agent review, exact Surge 2 Step rules, exact Vanguard rules, and explicit human approval metadata are still required later.

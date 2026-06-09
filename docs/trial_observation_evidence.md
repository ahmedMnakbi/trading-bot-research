# Trial Observation Evidence

Trial monitor-only evidence is a review package. It is not approval to trade Trial, Surge 2 Step, Vanguard, Challenge, Verification, Funded, or live accounts.

## Evidence Classes

- `trial_monitor_smoke`: short first-attachment evidence for informal review only.
  This may include edited or cleaned log excerpts and manual notes, but it is
  not formal Trial evidence and cannot approve trading.
- `formal_trial_observation`: complete Trial monitor-only evidence with raw
  Experts/Journal logs or raw MT5 log files and all required manual notes.
- `strategy_tester`: Strategy Tester evidence. It is useful later, but it is
  separate from Trial monitor-only observation evidence.

Edited or cleaned log excerpts are acceptable for informal smoke review only.
Raw MT5 Experts/Journal logs are required for formal audit and should be copied
unchanged. Do not edit, summarize, trim, or clean formal log files.
Do not provide passwords, investor passwords, API keys, prop credentials, or tokens.

## Required Evidence

- source scan PASS
- compile PASS
- safe TrialRiskFree settings with `EnableTrading=false`
- raw Experts/Journal logs or raw MT5 log files
- broker time verification note
- symbol session verification checklist
- no order placement evidence
- manual note confirming no orders and no positions during monitor-only observation

Optional evidence:

- screenshots folder
- Experts tab screenshot
- Journal screenshot
- Market Watch time/spread screenshots

Screenshots are optional for now. A formal package can pass without screenshots
when raw logs and all required notes are present.

## Collect

Use:

```powershell
python scripts/create_trial_observation_notes.py --run-id RUN_ID
python scripts/collect_trial_observation_evidence.py --evidence-kind trial_monitor_smoke --help
```

The collector copies user-provided evidence into `data/processed/trial_observation/{run_id}/`, redacts secret-like strings, excludes secret-like filenames, writes MQL5 source hashes, and records no-order-placement evidence.

For formal evidence, pass the folder or files containing raw MT5 logs through
`--ea-logs`. Raw log files are copied unchanged if they do not contain
secret-like values; files with secret-like names or values are excluded.
Do not provide passwords, investor passwords, API keys, or prop credentials.

Example formal collection without screenshots:

```powershell
python scripts/collect_trial_observation_evidence.py ^
  --evidence-kind formal_trial_observation ^
  --run-id RUN_ID ^
  --ea-logs path\to\raw_mt5_logs ^
  --settings-file data\processed\ea_settings\trial_monitor_only.set ^
  --compile-log data\processed\mql5_compile\compile_TIMESTAMP.log ^
  --source-scan data\processed\mql5_source_scan\source_scan.json ^
  --broker-time-note data\manual_evidence\RUN_ID\broker_time_note.txt ^
  --symbol-session-checklist data\manual_evidence\RUN_ID\symbol_session_note.txt ^
  --no-trial-trades-note data\manual_evidence\RUN_ID\no_order_no_position_note.txt
```

## Verify

Use:

```powershell
python scripts/verify_trial_observation_package.py data\processed\trial_observation\RUN_ID
```

Missing or non-raw monitor logs prevent formal evidence from passing because
Trial evidence cannot be complete without raw monitor-only EA logs. Smoke
evidence packages produce `WARN` because they are intentionally not formal Trial
observation evidence. Source scan, compile, safe settings, broker time
verification, symbol session verification, no-order evidence, and no-order/
no-position evidence are required for a complete formal review package.

Trial success is not prop challenge approval. Strategy Tester evidence and Final Audit Agent review are still required later. Exact Surge 2 Step rules and Vanguard rules remain unresolved and blocked.

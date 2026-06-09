# Strategy Tester Result Packaging

Phase 14.5 packages MT5 Strategy Tester results without screenshots. This is
local research evidence only. It does not approve Trial Risk-Free, Surge 2 Step,
Vanguard, Challenge, Verification, Funded, live-money trading, or profitability
claims.

## Export From MT5

After each tester run, save the exported Strategy Tester report and any tester
journal/log files into one local folder. Keep the `.set` file and generated
settings summary JSON with the same folder when possible.

Do not place credentials, account passwords, API keys, or private notes in the
folder. The collector skips secret-like file names and redacts secret-like text
patterns, but the safest workflow is to avoid collecting secrets at all.

## Parse One Run

```powershell
python scripts/parse_strategy_tester_report.py `
  path\to\tester_export_folder `
  --simulated-execution `
  --json
```

The parser extracts symbol, timeframe, date range, initial balance, final
balance, net profit, total trades, total deals, profit factor, drawdown,
strategy diagnostics, and tester execution diagnostics where present.

## Collect Evidence

```powershell
python scripts/collect_strategy_tester_evidence.py `
  --run-id tester_eurusd_m5_vwap_20260401_20260601 `
  --tester-artifacts path\to\tester_export_folder `
  --simulated-execution `
  --json
```

The output package is written under
`data\processed\strategy_tester_evidence\<run_id>\`. It contains copied local
artifacts, `parser_summary.json`, and `manifest.json`.

## Compare Runs

```powershell
python scripts/compare_strategy_tester_runs.py `
  data\processed\strategy_tester_evidence\tester_eurusd_m5_orb_20260401_20260601 `
  data\processed\strategy_tester_evidence\tester_eurusd_m5_vwap_20260401_20260601 `
  --output-md data\processed\strategy_tester_evidence\eurusd_m5_orb_vwap_compare.md `
  --output-json data\processed\strategy_tester_evidence\eurusd_m5_orb_vwap_compare.json
```

Use a small matrix first: EURUSD M5, ORB, VWAP, one recent one-month window, and
one recent two-month window. Do not optimize yet.

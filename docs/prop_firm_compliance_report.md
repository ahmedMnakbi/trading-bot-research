# Prop-Firm Compliance Report

Phase 7 adds local report tooling for native EA review evidence. Python remains a support layer for scanning, settings, log parsing, and reporting. It is not the execution layer.

Use:

```powershell
python scripts/export_prop_compliance_report.py ^
  --source-scan-path data/processed/mql5_source_scan/latest.json ^
  --compile-log-path data/processed/mql5_compile/compile_latest.log ^
  --settings-summary-path data/processed/ea_settings/trial_monitor_only.summary.json ^
  --log-summary-path data/processed/ea_log_summaries/latest.json ^
  --trial-evidence-path data/processed/trial_observation/<trial_evidence_id> ^
  --strategy-tester-evidence-path data/processed/strategy_tester_evidence/<tester_evidence_id>
```

The report writes JSON and Markdown under `data/processed/prop_compliance_reports/`. Missing evidence is allowed, but the report marks evidence incomplete.

Evidence is split by purpose. Source scan, compile log, and settings summary can be complete as build evidence while real EA monitor logs, Trial observation evidence, and Strategy Tester evidence remain incomplete. Missing or skipped real EA monitor logs are not treated as monitor evidence. Missing Trial evidence is not treated as Trial completion. Missing Strategy Tester output is not treated as tester completion.

Formal Trial observation evidence may remain skipped or incomplete while local
Strategy Tester evidence is present separately. Strategy Tester evidence does
not approve Surge 2 Step, Vanguard, Challenge, Verification, Funded, live use,
or profitability claims.

The report includes Upcomers rule mapping for 4% daily and 7% overall limits, the stricter EA limits, the 180-second minimum hold guard, prohibited behavior status, trading-disabled defaults, and the statement that Python is not the execution layer.

Account programs are tracked as `TrialRiskFree`, `Vanguard`, `Surge2Step`, and `Custom`. Trial Risk-Free remains the first testing account. Surge 2 Step remains rule-unverified until exact rules are reviewed and encoded. Vanguard remains blocked until exact rules, trial evidence, source scan PASS, compile PASS, final audit package, and explicit human approval metadata exist. Daily reset timezone confirmation and exact Dynamic Risk Shield calculation remain unresolved blockers before protected-stage use.

Phase 8 audit packages consume this report as one evidence input. A compliance report may have complete source/compile/settings evidence while still marking monitor logs, Trial observation, and Strategy Tester evidence incomplete.

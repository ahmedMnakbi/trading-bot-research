# Native MQL5 EA Audit Package

Phase 8 exports a local audit package under `data/processed/ea_audit_packages/{package_id}/`.
It is for source review, compile review, settings review, manual install review, and later Final Audit Agent review.

The package is intentionally honest. Source scan, compile log, generated settings, and prop compliance evidence can be present while real Trial monitor-only EA logs, Trial observation evidence, Strategy Tester evidence, daily reset timezone confirmation, Dynamic Risk Shield confirmation, Surge 2 Step rules, Vanguard rules, human approval metadata, and Final Audit Agent review remain missing.

Formal Trial observation evidence can remain skipped/incomplete while Strategy
Tester evidence is present separately under `data/processed/strategy_tester_evidence/`.
Neither evidence class is approval for protected account use or profitability
claims.

Use:

```powershell
python scripts/export_ea_audit_package.py ^
  --source-scan-path data/processed/mql5_source_scan/phase8_source_scan.json ^
  --compile-log-path data/processed/mql5_compile/compile_latest.log ^
  --settings-summary-path data/processed/ea_settings/trial_monitor_only.summary.json ^
  --prop-compliance-report-path data/processed/prop_compliance_reports/latest.json
```

The exporter snapshots docs and MQL5 source, hashes MQL5 and support source files, redacts secret-like strings, and excludes `.env` or credential-like files. It does not copy `data/processed` recursively into itself.

The package must not be read as approval for Trial trading, Surge 2 Step, Vanguard, Challenge, Verification, Funded, live money, or profitability claims. It may support source review, compile review, manual install review, and Trial monitor-only testing only after the before-Trial blockers are resolved or explicitly accepted.

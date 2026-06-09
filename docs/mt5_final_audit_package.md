# MT5 Final Audit Agent Package

The final Upcomers prop-firm execution path is a native MQL5 Expert Advisor. Python-controlled MT5 execution is quarantined as legacy non-prop-compatible code and must not be used for Challenge, Verification, Funded, Surge 2 Step, Vanguard, or other prop deployment.

The MT5 Final Audit Agent package is a review artifact for the native-EA release candidate. It snapshots MT5 planning documents, the transformation config, safety flags, safety-audit outputs, source-scan evidence, compile evidence when available, and an index of available MT5 evidence artifacts.

## Command

```powershell
python -m trading_bot export-mt5-final-audit-package --config config/default.yaml --mt5-transformation-config config/mt5_transformation.yaml
```

## Included Evidence

- MT5 roadmap, architecture, safety model, symbol mapping, data ingestion, strategy research, execution gates, and final audit checklist.
- MT5 transformation config snapshot.
- Safety audit report and scanner snapshots.
- Evidence index for MT5 rates, backtests, validations, campaigns, monitor runs, source scans, compile logs, and audits.
- Explicit safety flags proving Python MT5 execution, live trading, real orders, private API use, balance fetching, and position fetching remain disabled.
- Challenge, Verification, and Funded presets remain disabled unless trial evidence, source scan PASS, compile PASS, audit package ID, explicit human approval metadata, daily reset timezone verification, and Dynamic Risk Shield verification are present.

This package is not live approval. It is an input for Final Audit Agent and human review before any later live-pilot design can be considered.

# Safety Audit

The safety audit checks source code, configuration, environment variable names, generated artifacts, governance settings, and artifact integrity.

`PASS` means no failures or warnings were found. `WARN` means audit signals need review but do not fail the run. `FAIL` means a configured safety rule was violated.

A passing audit is not live approval. It only confirms local checks at the time of the audit.

Code scans search for prohibited order, private API, leverage, balance, transfer, and secret-related patterns. Explicit rejection guards are allowlisted so safety code can mention forbidden behavior.

Config scans verify live trading is disabled, real orders are not allowed, private API use is not allowed, stop-loss is required, leverage and shorting are disabled, the kill switch is armed, and risk per trade is capped.

Environment scans inspect variable names and redact values. Secret-like names produce warnings. Secret value leakage in local files is a failure.

Artifact scans inspect generated metadata and fail if any artifact claims live trading, real orders, or private API usage.

Artifact manifests hash every regular file in a directory except the manifest itself. Verification detects modified, missing, and extra files.

Failures should be treated as blockers for further review until resolved.


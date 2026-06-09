# Artifact Registry

The run registry scans `data/processed` and indexes backtests, validations, campaigns, paper runs, portfolio paper runs, reports, audits, failure tests, and incidents.

Build it with:

```bash
python -m trading_bot index-artifacts
```

The registry records run id, run type, path, creation time, metadata, safety flags, warnings, and available artifacts. Artifact indexing records relative path, size, modified time, SHA256, and artifact kind.

Missing metadata does not crash indexing. The run is included with a warning. Metadata that claims live trading, real orders, or private API usage is flagged as unsafe.

Archives are created with `archive-run` and only include files under `data/processed`. `.env` and secret-like files are excluded. Registry output and archives are review aids only; they are not live-trading approval.

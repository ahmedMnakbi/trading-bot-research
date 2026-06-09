# Release Candidate

Build a release candidate:

```bash
python -m trading_bot build-release-candidate --config config/default.yaml
```

Verify it:

```bash
python -m trading_bot verify-release-candidate --release-dir data/processed/releases/0.1.0-rc1
```

Release verification checks required files, non-live metadata, safety summaries, feature matrix snapshots, release checklist text, limitations, and absence of `.env` or sensitive-named files.

Reject a release candidate if any metadata claims live trading, real orders, or private API usage.

# Incident Replay

Incident replay reconstructs a local timeline from run artifacts. It reads state snapshots, metadata, decisions, health events, and alerts from an existing run directory, then writes an incident report under `data/processed/incidents`.

Run replay:

```bash
python -m trading_bot replay-incident --config config/default.yaml --run-dir data/processed/portfolio_paper/<portfolio_paper_run_id>
```

Timeline reconstruction sorts available decision, health, and alert events by timestamp. Missing or malformed artifacts are preserved as replay findings instead of causing exchange calls or live actions.

Safety outcomes are:

- `SAFE_SHUTDOWN`: a kill switch or stop condition activated and no later orders occurred.
- `SAFE_CONTINUATION`: the issue was contained and the system continued without breaking limits.
- `UNSAFE_STATE_DETECTED`: corrupted state, missing critical metadata, inconsistent state, or decisions after shutdown.
- `INSUFFICIENT_ARTIFACTS`: required local artifacts are missing.

Operators should review the suspected failure point, state summary, decisions, alerts, and health events. Incident replay is limited by the artifacts available on disk and is not approval for live trading or real-money deployment.

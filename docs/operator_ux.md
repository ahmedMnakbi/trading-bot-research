# Operator UX

Operator commands help navigate the non-live project without weakening safety controls.

List profiles:

```bash
python -m trading_bot list-profiles
```

Inspect an effective config:

```bash
python -m trading_bot show-profile --profile research
```

List and inspect runs:

```bash
python -m trading_bot index-artifacts
python -m trading_bot list-runs
python -m trading_bot show-run --run-id <run_id>
```

Find reports and archive runs:

```bash
python -m trading_bot latest-report
python -m trading_bot archive-run --run-id <run_id>
```

Run the offline smoke workflow:

```bash
python scripts/operator_smoke.py
```

These commands do not approve live trading. They are navigation and review helpers for local artifacts.

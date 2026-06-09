# EA Log Parser

Phase 7 adds a tolerant parser for monitor-only native EA logs. It does not connect to MT5, use credentials, or control orders.

Use:

```powershell
python scripts/parse_ea_logs.py --log-dir data/raw/ea_logs
```

The parser supports JSONL logs and plain text EA logs. If logs are missing, it writes a `SKIPPED` summary instead of failing. Summaries are written under `data/processed/ea_log_summaries/`.

The summary counts decisions by strategy, skip reasons, setup-forming records, entry and exit intents, refused trade actions, messages/day, trades/day, safety blocks, unresolved-rule warnings, minimum-hold warnings, spread blocks, and session blocks.

Entry intents in logs are monitor-only signals. The parser does not treat them as executed trades.

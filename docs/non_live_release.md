# Non-Live Release

The non-live release includes config validation, fixture OHLCV data, data inspection, backtesting, validation, campaigns, simulated paper trading, portfolio paper trading, reports, failure injection, incident replay, safety audits, artifact registry, and archive helpers.

It does not include live trading, real exchange order placement, authenticated exchange clients, private account endpoints, leverage, shorting, optimization, machine learning, dashboard servers, or external alert integrations.

Run the release smoke workflow:

```bash
python -m trading_bot run-nonlive-smoke --config config/default.yaml
```

Release artifacts summarize the fixture-only workflow and safety metadata. They are review artifacts only and are not live-trading approval.

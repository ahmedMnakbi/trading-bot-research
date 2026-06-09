# Operator Runbook

Use the Python commands below as the canonical cross-platform workflow.

```bash
python -m trading_bot validate-config --config config/default.yaml
python -m trading_bot fetch-ohlcv --exchange kraken --symbol BTC/USDT --timeframe 4h --since-days 365
python -m trading_bot inspect-data --exchange kraken --symbol BTC/USDT --timeframe 4h
python -m trading_bot run-backtest --config config/default.yaml --exchange kraken --symbol BTC/USDT --timeframe 4h --strategy donchian_breakout
python -m trading_bot run-validation --config config/default.yaml --exchange kraken --symbol BTC/USDT --timeframe 4h
python -m trading_bot run-campaign --config config/default.yaml --exchange kraken
python -m trading_bot run-paper --config config/default.yaml --exchange kraken --symbol BTC/USDT --timeframe 4h --strategy donchian_breakout --validation-run-id <validation_run_id>
python -m trading_bot report-paper --config config/default.yaml --paper-run-id <paper_run_id> --validation-run-id <validation_run_id>
python -m trading_bot run-safety-audit --config config/default.yaml
```

Before a review checkpoint, run:

```bash
python scripts/check_all.py
```

## Forbidden Commands / Forbidden Work

This project still must not run real orders, private API clients, balance fetches, account endpoints, leverage, shorting, or live trading. Do not add authenticated exchange clients, private exchange connectors, real order placement, parameter optimization, machine learning, profitability claims, dashboard servers, or external alert integrations.

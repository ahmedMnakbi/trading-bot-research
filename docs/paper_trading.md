# Paper Trading

Task 6 adds a public-data paper trading loop. Paper trading is not live trading: every order is simulated, no private exchange API is used, no balances are fetched, and real orders remain forbidden.

## Public Data Limits

Public OHLCV data may be stale, incomplete, delayed, duplicated, or missing candles. The paper engine validates batches, avoids reprocessing already handled candles, tracks data errors, and can activate the kill switch after repeated failures.

## Simulated Fills

Simulated fills use the same conservative fee and slippage assumptions as backtesting. These fills are not guaranteed to match real exchange fills.

## Validation Gate

Paper trading requires a completed validation run by default. This ensures a strategy has passed the fixed-parameter validation workflow before being run in a live-like loop.

## State Persistence

Paper state is written under `data/processed/paper/{paper_run_id}/state.json` with Parquet order, trade, and equity-curve artifacts. Runs can resume existing state when configured.

## Decision Logs

Every processed candle writes a JSONL decision record with the strategy intent, risk decision, simulated order decision, before/after position state, and explicit `live_trading: false` and `real_order: false` markers.

## Health Events And Alerts

Health events are written to `health_events.jsonl`. Alerts are written to `alerts.jsonl` for important events such as data failures, risk rejection, order rejection, or kill-switch activation. No external messaging integration is included.

## Stopping And Resuming

Use `--max-iterations` to stop a paper loop after a fixed number of polling iterations. Resume behavior is controlled by `paper.resume_existing_state`.

## Real Orders Remain Forbidden

Task 6 does not include authenticated clients, private endpoints, real order placement, leverage, short selling, optimization, machine learning, or profitability claims.

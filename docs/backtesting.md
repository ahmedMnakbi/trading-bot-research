# Backtesting

Task 3 adds deterministic local backtesting from validated OHLCV cache files. It does not call exchanges, trade live prices, optimize parameters, or make profitability claims.

## Why Backtesting Can Be Misleading

Backtests can look profitable because of bad data, missing fees, missing slippage, look-ahead bias, survivorship bias, or accounting bugs. The first backtesting milestone proves simulation behavior before any real strategy work.

## Why Same-Candle Fills Are Forbidden

A signal generated at a candle close cannot know or trade that same candle's open, high, or low. Same-candle fills can accidentally use information that was not available at decision time.

## Why Next-Open Fills Are Used

Signals are generated from candles available through the current close. Simulated trades fill at the next candle open, which keeps execution ordering deterministic and avoids look-ahead.

## Fees And Slippage

Fees are charged on notional value using `fee_bps`. Slippage is applied against the trader: buys fill above the next open and sells fill below the next open using `slippage_bps`.

## Buy-And-Hold Benchmark

`buy_and_hold` is a benchmark only. It buys once and exits at the end so other future strategies can be compared with a simple baseline. It is not a live-trading recommendation.

## No Optimization Yet

Parameter optimization is intentionally prohibited. The project must first prove that cached data replay, fills, risk rejection, metrics, and artifacts are reliable.

## Artifacts

Each run writes:

- `config_snapshot.yaml`
- `metrics.json`
- `equity_curve.parquet`
- `trades.parquet`
- `orders.parquet`
- `run_metadata.json`

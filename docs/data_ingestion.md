# Data Ingestion

Task 2 adds read-only public OHLCV ingestion before any strategy or backtesting work.

## Why OHLCV Data May Be Incomplete

Exchange OHLCV feeds can have missing intervals, delayed candles, symbol outages, maintenance windows, and latest candles that are still forming. The ingestion layer validates continuity and drops the latest incomplete candle by default.

## Why Rate Limits Matter

Public endpoints are still rate limited. The CCXT provider enables rate limiting and retries transient network or rate-limit failures so data collection is polite and repeatable.

## Why Raw Data Is Cached Before Backtesting

Raw Parquet cache files make later research reproducible. Backtests should run against a stable local dataset rather than repeatedly pulling mutable exchange responses.

## Why Validation Comes Before Strategy Testing

Strategy results are only as reliable as their inputs. Duplicate timestamps, non-monotonic rows, malformed OHLCV values, or missing candle gaps can create misleading signals and false performance expectations.

Task 2 does not include strategy signals, position sizing, portfolio simulation, live trading, or any private exchange client.

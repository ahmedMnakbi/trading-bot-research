# MT5 Data Ingestion

MT5 data ingestion is read-only and research-only. It does not implement live trading, real order placement, authenticated account trading, balance fetching, or position management.

The MT5 data layer reads candle/rate data from the local terminal, converts timestamps to UTC and `America/New_York`, stores spread-aware local Parquet caches, and reports missing, duplicate, invalid, stale, and incomplete data conditions. Historical range fetches and bounded recent-rate polling are both read-only.

## Safety Boundary

- Allowed: read historical rates, poll recent rates, cache data, inspect data quality, and test New York session conversion.
- Forbidden: account reads, position reads, order preflight, order submission, live account trading, balance fetching, leverage, martingale, grid trading, and averaging down.

## Timestamp Rules

- MT5 epoch timestamps are stored as UTC.
- Broker/server datetime values must be converted with an explicit broker timezone.
- Every cached bar includes `timestamp` in UTC and `new_york_timestamp` in `America/New_York`.
- EST New York session windows use UTC-05:00.
- EDT New York session windows use UTC-04:00.

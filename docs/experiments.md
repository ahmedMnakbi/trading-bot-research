# Experiments

An experiment is one fixed-parameter strategy evaluation for one exchange, symbol, and timeframe.

Campaigns form a matrix from configured symbols, timeframes, and strategies. Each row runs required stages such as backtest and validation using cached historical OHLCV.

Parameters remain fixed. Campaigns do not optimize, search, or tune.

Cached data is used by default so runs are reproducible and do not depend on live public responses.

Failed experiments are isolated and written to `failed_runs.json`; one failed row does not invalidate the entire campaign.

Campaign results are not profit claims. They are historical diagnostics for deciding what deserves more paper-trading review.


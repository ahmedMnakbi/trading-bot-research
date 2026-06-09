# Paper Reporting

Paper reports analyze local paper-trading artifacts: state, orders, trades, equity curve, health events, alerts, and optional validation/backtest references.

Metrics are calculated from the persisted paper account and Parquet artifacts. If trades or equity history are too sparse, metrics are returned as `null` where appropriate and warnings are emitted instead of crashing.

Health events and alerts affect readiness because data errors, state failures, order rejections, and kill-switch activity can invalidate a live-like paper run even when simulated returns look acceptable.

Optional validation and backtest comparisons measure return degradation, drawdown worsening, profit factor, and trade counts. Missing comparison data is handled as a warning.

Paper results are not profit claims. Simulated fills can diverge from real fills, public data can be stale, and historical behavior does not imply future performance.

Reports are not live-trading approval. They only summarize configured readiness gates and whether a run is eligible for human review.


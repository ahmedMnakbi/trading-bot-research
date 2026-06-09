# Release Checklist

## Code Quality

- [ ] `python -m ruff check .` passes.
- [ ] `python -m pytest` passes.
- [ ] No unrelated generated files are included in review.

## Configuration Safety

- [ ] `python -m trading_bot validate-config --config config/default.yaml` passes.
- [ ] Default mode remains `paper` or `backtest`, never `live`.
- [ ] `live_trading_enabled` remains `false`.

## Data Safety

- [ ] Fixture data can be generated without internet access.
- [ ] Raw cached OHLCV is not deleted unless explicitly requested.
- [ ] CI does not require exchange API keys or account secrets.

## Backtesting

- [ ] Fixture backtest flows produce expected artifacts.
- [ ] Backtests use cached data and simulated fills only.
- [ ] Backtest metadata does not claim live trading or real orders.

## Validation

- [ ] Validation flows run from cached data.
- [ ] Walk-forward outputs are artifacted.
- [ ] Validation metadata records fixed parameters and no optimization.

## Campaigns

- [ ] Fixed-parameter campaigns run from cached data.
- [ ] Candidate labels are conservative review signals only.
- [ ] Campaign reports include limitations and no profitability claim.

## Paper Trading

- [ ] Paper flows use simulated execution only.
- [ ] Paper reporting requires validation references where configured.
- [ ] Paper results are not live-trading approval.

## Reporting

- [ ] Reports include safety and readiness context.
- [ ] Reports avoid profitability claims.
- [ ] Reports point to the artifacts they summarize.

## Safety Audit

- [ ] `python -m trading_bot run-safety-audit --config config/default.yaml` passes.
- [ ] No real order-placement code is present.
- [ ] No authenticated exchange client or private account endpoint is present.

## Artifact Integrity

- [ ] Artifact manifests are written where required.
- [ ] Manifest verification passes for reviewed artifacts.
- [ ] Generated artifacts are reproducible or traceable.

## Human Review

- [ ] A human reviewer has inspected code, config, artifacts, and audit output.
- [ ] Any warnings are understood and documented.
- [ ] Human review does not override the live-trading prohibition.

## Live Trading Status

Live trading is not implemented and is not approved. Real orders, authenticated exchange clients, private account endpoints, leverage, and short selling remain forbidden.

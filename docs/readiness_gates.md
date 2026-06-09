# Readiness Gates

Readiness gates are safety and review checks, not profit targets.

## Statuses

- `NOT_READY`: a hard safety gate failed.
- `NEEDS_MORE_PAPER_TRADING`: hard safety gates passed, but runtime, trade count, or metric coverage is insufficient.
- `ELIGIBLE_FOR_HUMAN_REVIEW`: configured gates passed and the run may be reviewed by a human.

`ELIGIBLE_FOR_HUMAN_REVIEW` is not live approval.

## Gates

- Live trading must be false.
- Real orders must be false.
- Private API usage must be false.
- State corruption must be absent when required.
- Kill switch must be inactive when required.
- Drawdown and daily/weekly loss must stay within configured limits.
- Unresolved alerts must not exceed the configured limit.
- A validation reference must exist when required.
- Minimum paper runtime and trade count must be met.
- Human approval must remain mandatory before live deployment.

Real execution remains forbidden in this project stage. No authenticated exchange client or real-order pathway is introduced by reporting.


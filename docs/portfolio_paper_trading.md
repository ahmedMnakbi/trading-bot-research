# Portfolio Paper Trading

Multi-symbol paper trading is needed because a strategy can look safe in a single-symbol loop while failing once several symbols compete for the same simulated cash. Task 11 adds a portfolio paper engine that processes configured symbols together and keeps one shared portfolio state.

## Shared Simulated Cash

The portfolio starts with one cash balance. Accepted simulated entries reduce that shared cash, and exits return simulated proceeds to it. Portfolio equity is cash plus marked open-position value. This keeps duplicate signals and oversized combined exposure visible.

## Per-Symbol Strategy Mapping

`portfolio_paper.strategy_map` assigns one fixed strategy to each configured symbol. The engine evaluates each symbol independently, then applies portfolio risk checks before any simulated order is created.

## State Persistence

Portfolio paper state is persisted under `data/processed/portfolio_paper/{portfolio_paper_run_id}/`. The run directory includes `state.json`, orders, trades, equity curve, exposure snapshots, health events, alerts, and non-live run metadata.

## Campaign Gating

When `require_campaign_reference` is true, a completed campaign run directory must exist before portfolio paper trading can start. This makes campaign review a prerequisite for multi-symbol paper testing.

## Simulated Fills Only

Portfolio paper trading uses the simulated execution client. Simulated fills are not live fills and do not prove real exchange liquidity, latency, fees, slippage, or order-book behavior.

## No Real-Trading Approval

Portfolio paper output is evidence for human review only. It does not approve real-money trading, live execution, private API access, leverage, or short selling.

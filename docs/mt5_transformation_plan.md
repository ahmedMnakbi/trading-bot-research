# MT5 Transformation Plan

## Purpose

The project is being transformed toward an MT5-based, NY-session, multi-market monitoring bot. The intended markets are forex, gold, indices, crypto, and selected commodities where the broker exposes read-only symbol metadata.

Task 16 adds only a read-only MT5 foundation. It does not add live trading, order placement, account reads, balance reads, position reads, leverage, shorting, optimization, or ML.

## Final Direction

- Build an MT5 live-monitoring bot that can observe broker symbols, market data, session timing, spreads, and safety state.
- Focus strategy research on the New York session, with explicit handling for broker time zones and instrument-specific trading hours.
- Support forex, gold, indices, crypto, and commodities through broker-specific symbol mapping.
- Run demo first. Live operation can only be considered after historical evaluation, demo evidence, audit logs, risk review, and explicit human approval.
- Keep execution disabled until a separate reviewed task introduces any execution design.

## Why Transform Instead Of Discarding The Binance Bot

The existing Binance direction already created useful non-live foundations: configuration validation, safety defaults, structured logs, artifact indexing, safety audits, backtests, validations, campaigns, and paper-state reporting. Those pieces remain valuable even if the data and broker interface change.

Transforming the project preserves the safety-first workflow and avoids throwing away proven guardrails. The exchange-specific parts can be replaced with MT5 adapters over time, while the non-live audit discipline, reporting structure, and human-approval gates stay intact.

## Phases

1. Read-only MT5 discovery: validate config, initialize a local terminal connection if available, inspect terminal status, and list symbol metadata only.
2. Symbol mapping and market data planning: classify broker symbols, identify time zones, spreads, stop levels, volume constraints, and trading sessions.
3. Historical and demo data evaluation: compare broker data quality, session filters, fee/spread assumptions, and slippage assumptions.
4. Demo-only monitoring: observe decisions and simulated risk behavior without account or position access.
5. Live-readiness review: require audit logs, demo results, safety review, rollback plan, and human approval before any live-capable design.

## Current Non-Live Boundary

The current boundary is read-only terminal discovery. The connector must not call execution, account, or position APIs. The CLI must fail gracefully if the MetaTrader5 package or local terminal is unavailable.

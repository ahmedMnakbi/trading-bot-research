# MT5 Transformation Roadmap

The final Upcomers prop-firm execution path is a native MQL5 Expert Advisor. Python-controlled MT5 execution is quarantined as legacy non-prop-compatible code and must not be used for Challenge, Verification, Funded, Surge 2 Step, Vanguard, or other prop deployment.

## Phase 0 - Current State Freeze

Document that the project is v0.1.0-nonlive. Live trading, real orders, authenticated execution, private account endpoints, and live approval are not implemented. Immediately quarantine Python MT5 execution from prop-compatible workflows. The existing repo remains the foundation.

## Phase 1 - MT5 Read-Only Foundation

Support safe package availability checks, optional read-only terminal initialization, terminal status, symbol discovery, symbol metadata, and broker-specific symbol classification. Execution and account functions remain forbidden.

## Phase 2 - MT5 Historical Data Ingestion

Read historical MT5 rates for research only. Cache M1/M5/M15/H1 data, validate OHLCV/spread/timestamps, inspect missing and duplicate candles, and convert broker/server time to `America/New_York`.

## Phase 3 - NY Session Strategy Engine

Implement signal detection only for opening range breakout, VWAP trend continuation, dynamic noise-band momentum plus VWAP stop, London/New York overlap momentum, and volume/volatility expansion. Signals do not place orders.

## Phase 4 - MT5 Backtesting and Validation

Adapt the existing backtesting, validation, walk-forward, and campaign framework to MT5 markets with spread, slippage, commission placeholders, lot constraints, point values, min stop distance, and session-only trading.

Initial cached-data MT5 backtesting, static split validation, walk-forward evaluation, and campaign review are implemented for local research simulation.

## Phase 5 - Strategy Campaigns On MT5 Data

Run campaigns across reviewed MT5 symbols and strategies. Outputs are rankings, warnings, candidate labels, market suitability notes, and evidence quality. Labels are for paper/demo observation only.

## Phase 6 - Native EA Monitor-Only Skeleton

Create the native MQL5 EA skeleton with monitor-only defaults, account staging, manual confirmation inputs, logging, symbol/session plumbing, and no trading-enabled behavior.

## Phase 7 - Native EA Risk And Compliance Guards

Add source-scanned MQL5 risk/compliance guards: missing stops, unsafe spreads, unsafe lots, unsafe stop distances, max trades/day, message counter, minimum hold time, daily/overall loss guards, and approval gates.

Challenge, Verification, and Funded presets remain disabled unless trial evidence, source scan PASS, compile PASS, audit package ID, explicit human approval metadata, daily reset timezone verification, and Dynamic Risk Shield verification are present.

## Phase 8 - Trial MT5 Platform Observation

Use the Trial Risk-Free 10K account as the first MT5 platform testing environment. Trial success is not approval for Surge 2 Step, Vanguard, or funded trading. Surge 2 Step 5K remains rule-unverified until exact rules are reviewed and encoded.

## Phase 9 - Final Audit Agent Review

Package code, configs, strategy evidence, demo results, audit logs, reports, execution gates, and risk controls for external audit before any live pilot design.

## Phase 10 - Prop Challenge Readiness Design

Design only. Vanguard 2K remains protected until exact rules, Trial evidence, source scan PASS, compile PASS, Final Audit Agent review, audit package ID, and explicit human approval metadata exist.

## Phase 11 - Explicitly Approved Prop Deployment Work

Only after explicit user approval and audit. Any prop deployment remains locked behind native MQL5 EA implementation, environment gates, config gates, source scans, compile checks, manual confirmation, exposure caps, and kill-switch gates.

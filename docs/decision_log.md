# Decision Log

## 2026-05-30: Start with a custom safety-first skeleton

The project starts with a small custom skeleton instead of immediately forking Freqtrade or building a live exchange connector because the first milestone is safety behavior, not trading capability. A minimal codebase makes the default mode, live-trading gate, kill switch, logging redaction, and risk validation easy to inspect and test before introducing framework complexity or any real order path.

## 2026-05-30: Add read-only public OHLCV ingestion before strategy/backtesting work

Strategy results are only as reliable as the data. The project will not begin backtesting until data ingestion, caching, and validation are tested. This also preserves the safety boundary: Task 2 uses public market-data endpoints only and cannot place trades.

## 2026-05-30: Build a deterministic backtesting engine before strategy optimization

The project must prove that simulation, fills, fees, slippage, risk rejection, metrics, and result artifacts work correctly before testing real strategies. This reduces the risk of false profitability caused by look-ahead bias, missing fees, same-candle fills, or broken accounting.

## 2026-05-30: Add fixed-parameter baseline strategies before optimization

The project needs transparent strategy mechanics, stop-loss-aware trade intents, and risk-based position sizing before any parameter search. This avoids creating false confidence from overfitted backtests and keeps the focus on correctness, risk controls, and auditability.

## 2026-05-30: Add out-of-sample and walk-forward validation before optimization or paper trading

A strategy that looks good on one historical period may fail out of sample. The project must evaluate fixed-parameter baselines across chronological splits, rolling windows, benchmarks, and market regimes before any parameter search or paper-trading work begins.

## 2026-05-30: Add public-data paper trading before any real execution connector

The project needs to prove that strategy decisions, risk checks, state persistence, simulated execution, health monitoring, alerts, and kill-switch behavior work in a live-like loop before any authenticated exchange or real-order code is introduced.

## 2026-05-30: Add reporting and readiness gates before any real execution connector

Paper trading can still produce misleading confidence. The project must summarize performance, health, alerts, drawdowns, validation comparison, and safety gates before even considering live-execution design. Passing readiness gates only makes a run eligible for human review; it does not approve live trading.

## 2026-05-30: Add automated safety audits and artifact integrity before any real execution work

Manual greps and informal review are not enough for a financial automation project. The project needs repeatable checks for prohibited code paths, unsafe config, secret leakage, artifact tampering, and governance violations before any future work on authenticated exchange connections can be considered.

## 2026-05-30: Add fixed-parameter experiment campaigns before any live-execution work

Individual backtests and validations can be cherry-picked. The project needs repeatable campaign-level evaluation across configured symbols, timeframes, strategies, benchmarks, warnings, and failures before deciding which candidates deserve more paper-trading review.

## 2026-05-30: Add CI and reproducible safety gates before any real execution work

Manual verification is not enough. Every future change must pass automated tests, linting, config validation, safety audit, and reproducible fixture-based checks before the project can move toward any human review checkpoint.

## 2026-05-30: Add multi-symbol simulated portfolio paper trading before any real execution connector

A bot can pass single-symbol paper tests while still failing at the portfolio level through overexposure, duplicated signals, shared-cash conflicts, correlated positions, or portfolio drawdown. Multi-symbol simulated paper trading is required before any authenticated execution design can be considered.

## 2026-05-30: Add failure injection and incident replay before any real execution connector

A trading bot must fail safely under stale data, corrupted state, strategy exceptions, rejected orders, write failures, and interruptions. Simulated failure testing and incident replay are required before any authenticated exchange design can be considered.

## 2026-05-30: Add operator UX, config profiles, run registry, and artifact navigation before polishing the non-live release

The project now produces many artifacts and commands. Operators need safe profiles, run discovery, artifact indexing, latest-report helpers, safe archiving, and a clear workflow so the system can be used without weakening the non-live safety boundary.

## 2026-05-30: Add non-live release candidate packaging and end-to-end smoke verification

The project is now large enough that individual command tests are insufficient. A release candidate must prove the full fixture-based workflow works end-to-end, produces auditable artifacts, passes safety checks, and clearly states that live trading and real-money deployment remain forbidden.

## 2026-05-30: Finalize the v0.1 non-live release with install checks, final safety verification, and a human review package

The project has reached a usable non-live research and paper-trading release candidate. Before calling it ready to use, it needs installation verification, complete operator documentation, final non-live safety checks, and a human-review package that clearly states the system is not approved for real-money trading.

## 2026-05-31: Transform the non-live framework toward MT5 instead of discarding it

The final product direction is shifting from Binance/public-crypto research toward an MT5 New York-session multi-market native MQL5 EA. The existing project is preserved because its config validation, safety defaults, research workflow, reporting, artifact integrity, incident replay, safety audit, governance gates, and operator UX are still valuable. The Binance work remains historical research evidence, while MT5-specific symbol mapping, data ingestion, strategy research, source scanning, settings generation, log parsing, and audit packaging will be added through gated phases rather than replacing the safety-first foundation.

# Trading Bot

Safety-first trading research and native MT5 EA project.

This project is intentionally inert in Task 1. It does not place real orders, does not connect to live exchange execution, and does not perform strategy optimization. Live trading is disabled by default and must remain blocked unless explicit environment and configuration approvals are both present.

The primary product direction is now the Upcomers native MQL5 Expert Advisor path. The MQL5 source is monitor-only and not execution-ready: it can be scanned and compiled, but it must not place orders or control prop accounts. The earlier Binance/crypto work remains useful as legacy research, validation, reporting, and safety infrastructure; it is not the current prop-firm execution direction.

## Quick Start

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
pip install -e .
python -m trading_bot --help
python -m trading_bot validate-config --config config/default.yaml
python -m trading_bot fetch-ohlcv --exchange kraken --symbol BTC/USDT --timeframe 4h --since-days 30
python -m trading_bot inspect-data --exchange kraken --symbol BTC/USDT --timeframe 4h
python -m trading_bot run-backtest --exchange kraken --symbol BTC/USDT --timeframe 4h --strategy noop
python scripts/generate_fixture_data.py
python scripts/check_all.py
pytest
ruff check .
```

## Safety Defaults

- Default mode is `paper`.
- `mode: live` is rejected unless `ALLOW_LIVE_TRADING=true` is set and `live_trading_enabled: true` is present in config.
- Kill switch defaults to armed.
- Stop-loss is required.
- Leverage is forbidden.
- API secrets are redacted from logs.

No function in this repository can place real exchange orders in Task 1.

## Read-Only Market Data

Task 2 adds public OHLCV ingestion only. It uses CCXT public market-data endpoints, writes raw candles to local Parquet cache files, and stores metadata sidecars. No API keys are required.

The default config keeps `exchange: sandbox` as a non-live placeholder. Use CLI overrides for real public market data, for example `--exchange kraken`.

## Deterministic Backtesting

Task 3 adds local backtesting from cached OHLCV files. It makes no exchange calls and cannot place orders. Strategies emit signals only; fills, fees, slippage, risk rejections, and result artifacts are handled by the simulator.

Task 4 adds fixed-parameter Donchian breakout and EMA trend baselines with ATR stops. These are correctness fixtures and benchmarks, not profitability claims, and no optimization code is included.

Task 5 adds local out-of-sample and walk-forward validation with benchmark comparison and regime diagnostics. Parameters remain fixed and `optimization_used` is recorded as `false`.

Task 6 adds public-data paper trading with simulated execution only. It records state, decisions, orders, trades, health events, and alerts while keeping real orders forbidden.

Task 7 adds paper-trading reports and readiness gates. A report can mark a run as `ELIGIBLE_FOR_HUMAN_REVIEW`, but this is not approval for live trading.

Task 8 adds safety audits and artifact manifests. A `PASS` result is still not live-trading approval; it only confirms configured local safety checks.

Task 9 adds fixed-parameter experiment campaigns across cached symbols, timeframes, and strategies. Candidate labels are review signals only, not profitability claims.

Task 10 adds reproducible local and CI safety gates. On Windows and other platforms, prefer the Python script commands (`python scripts/check_all.py`, `python scripts/check_safety.py`, and `python scripts/clean_artifacts.py`) as the canonical workflow. The optional Makefile mirrors those commands for environments where `make` is available.

Task 11 adds multi-symbol portfolio paper trading with shared simulated cash, per-symbol strategy mapping, exposure snapshots, and portfolio risk controls. It still uses simulated execution only and is not approval for live trading.

Task 12 adds local failure injection and incident replay. These tools deliberately simulate dangerous conditions and reconstruct incidents from local artifacts only; they do not enable live trading or real execution.

Task 13 adds operator UX helpers: safe config profiles, run/artifact registry, latest-report lookup, safe archiving, and an offline operator smoke script.

Task 14 adds v0.1.0-rc1 non-live release candidate packaging and end-to-end fixture smoke verification. This is still not approved for real-money trading.

Task 15 finalizes v0.1.0-nonlive with install checks, onboarding docs, final non-live verification, and a human review package. It remains a non-live research and paper-trading release only.

## Upcomers Native MT5 EA Direction

The final Upcomers prop-firm execution path is a native MQL5 Expert Advisor. The current repository is not being discarded: its config validation, safety defaults, data validation, backtesting, validation, campaigns, paper trading, reporting, readiness gates, safety audit, artifact integrity, incident replay, operator UX, release checks, and human review package remain the foundation.

Python-controlled MT5 execution is quarantined as legacy non-prop-compatible code. Python remains support-only for research, read-only data work, validation, reporting, source scanning, settings generation, log parsing, audit package export, and human review packages.

Planning config lives in `config/mt5_transformation.yaml`, with MT5 and New York-session research disabled by default. Phase 13 adds a native MQL5 Trial Risk-Free micro-execution path that is also disabled by default and isolated to the free Trial account. Live-money trading, Surge 2 Step, Vanguard, Challenge, Verification, and Funded use remain not approved. The Trial Risk-Free 10K account is the first MT5 platform testing environment; it is not approval for Surge 2 Step, Vanguard, or funded trading.

The MT5 historical data foundation adds read-only `fetch-mt5-rates` and `inspect-mt5-data` commands for local terminal candle data, cache inspection, and New York timestamp conversion. These commands do not read balances, positions, or account state, and they do not place orders.

The New York-session strategy foundation adds signal-only setup detection for opening range breakout, VWAP trend continuation, dynamic noise-band momentum, London/New York overlap momentum, and volume/volatility expansion. These strategies emit research signals only; they do not connect to broker execution.

MT5 cached-data backtesting can simulate those NY-session signals from local MT5 rate caches with spread, slippage, fee, lot-size, and stop-distance assumptions. It writes review artifacts locally and remains research-only.

MT5 validation and campaigns now run static split, walk-forward, and multi-symbol/multi-strategy review over cached MT5 data. Candidate labels are research review signals only and do not approve Trial Risk-Free, Surge 2 Step, Vanguard, or funded execution.

Known account programs are `TrialRiskFree`, `Vanguard`, `Surge2Step`, and `Custom`. Surge 2 Step is rule-unverified and blocked until its exact rules are reviewed and encoded. Vanguard remains protected until exact rules, trial evidence, audit evidence, and human approval exist.

The legacy Python MT5 demo execution module is quarantined and must not be imported by prop-compatible workflows. The MT5 demo monitor is monitor-only: it can run bounded smoke checks from cached MT5 rates or read-only recent terminal rates, log every decision, track internal demo state, emit health events, and observe internal protective stop/target events without broker execution.

Daily loss reset timezone must be confirmed from current Upcomers rules before challenge use. Until confirmed, the EA/settings layer must expose configurable `PropDayResetTimezone` and default conservatively. Exact Dynamic Risk Shield calculation must also be verified from current Upcomers rules before Challenge, Verification, or Funded presets are enabled.

Before Trial observation, complete the hardening checklist in `docs/before_trial_observation_todo.md`.

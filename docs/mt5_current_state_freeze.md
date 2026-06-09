# MT5 Current State Freeze

The final Upcomers prop-firm execution path is a native MQL5 Expert Advisor. Python-controlled MT5 execution is quarantined as legacy non-prop-compatible code and must not be used for Challenge, Verification, Funded, Surge 2 Step, Vanguard, or other prop deployment.

## Frozen State

- Project status: native MQL5 EA with Phase 13 Trial Risk-Free micro-execution disabled by default.
- Live-money trading is not implemented.
- Real orders are allowed only through the isolated native MQL5 TrialExecution module after strict Trial Risk-Free gates pass.
- Authenticated broker or exchange execution is not implemented.
- Private account endpoints are not implemented.
- Python MT5 execution is quarantined as legacy non-prop-compatible code.
- Native MQL5 EA protected execution is not implemented yet.
- MT5 live-money execution is not implemented and not approved.
- Current Binance crypto strategy evidence is weak and not live-ready.
- Existing non-live infrastructure remains the foundation.
- Trial Risk-Free 10K is the first MT5 platform testing environment and is not approval for Surge 2 Step, Vanguard, or funded trading.
- Surge 2 Step 5K is rule-unverified and blocked until exact rules are reviewed and encoded.
- Vanguard 2K is protected and blocked until exact rules, trial evidence, audit package, and human approval exist.

## Preserved Infrastructure

The transformation keeps config validation, safety defaults, no-live governance, data validation, backtesting, validation, walk-forward testing, campaigns, paper trading, portfolio paper trading, reporting, readiness gates, safety audit, artifact integrity, incident replay, operator UX, release checks, and the human review package.

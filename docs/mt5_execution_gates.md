# MT5 Execution Gates

The final Upcomers prop-firm execution path is a native MQL5 Expert Advisor. Python-controlled MT5 execution is quarantined as legacy non-prop-compatible code and must not be used for Challenge, Verification, Funded, Surge 2 Step, Vanguard, or other prop deployment.

## Current State

Execution is disabled by default. Python MT5 execution is quarantined and not prop-compatible. Any future approved execution must be implemented in native MQL5 EA code with disabled defaults, strict manual confirmation, account staging, source scan PASS, compile PASS, audit package ID, trial evidence, and explicit human approval metadata.

## Required Gates Before Any Native EA Execution Implementation

- Account program labeling: `TrialRiskFree`, `Vanguard`, `Surge2Step`, and `Custom`.
- Account stage labeling: `MonitorOnly`, `Trial`, `Challenge`, `Verification`, and `Funded`.
- Surge 2 Step defaults are rule-unverified until exact rules are reviewed and encoded.
- Vanguard defaults remain protected until exact rules, trial evidence, audit package, and human approval exist.
- Config gate, environment gate, governance gate, and safety audit gate.
- Required stop-loss and take-profit rules.
- One-position-per-symbol rule.
- Max daily loss, max weekly loss, and max drawdown limits.
- Max spread and max slippage/deviation limits.
- Min lot, lot step, and min stop distance validation.
- Session filter and session-close handling.
- Kill switch and emergency stop.
- Reconciliation plan.
- Configurable `PropDayResetTimezone` until current Upcomers daily reset rules are confirmed.
- Verified Dynamic Risk Shield calculation before Challenge, Verification, or Funded presets.
- Audit log for every decision, request, rejection, and result.

## Forbidden Patterns

Martingale, grid trading, averaging down, hidden bypasses, executable leverage, Python MT5 execution, and live account trading are forbidden. A later native EA module must be isolated and must fail closed.

## Demo Monitor State

The MT5 monitor records decisions, health events, last processed candle, internal open position state, and kill-switch state. It can observe internal stop-loss and take-profit triggers from candle data without changing broker state. It does not use live account positions for reconciliation in this foundation; reconciliation must remain conservative until a later explicitly approved native EA phase.

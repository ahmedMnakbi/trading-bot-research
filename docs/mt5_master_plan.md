# MT5 Master Plan

The final Upcomers prop-firm execution path is a native MQL5 Expert Advisor. Python-controlled MT5 execution is quarantined as legacy non-prop-compatible code and must not be used for Challenge, Verification, Funded, Surge 2 Step, Vanguard, or other prop deployment.

## Current Direction

The project remains v0.1.0-nonlive and preserves the existing Binance/public-data research framework as reusable infrastructure. The future product direction is an MT5 New York-session multi-market native EA, not a Python execution bot.

## Target Capabilities

- Connect to MT5 through controlled, safety-gated modules.
- Discover broker-specific symbols and classify them as forex, gold, indices, crypto CFDs, commodities, or unknown.
- Ingest, cache, validate, and inspect MT5 historical candles.
- Convert broker/server timestamps to `America/New_York`.
- Apply DST-aware New York session filters.
- Research objective New York-session strategy families before any native EA execution.
- Backtest, validate, run campaigns, report warnings, and produce audit artifacts.
- Add native MQL5 EA execution only after research, validation, source scan PASS, compile PASS, safety audit, Final Audit Agent review, trial evidence, and explicit human approval.

## Safety Posture

Live trading is not implemented and not approved. Real order placement by Python, authenticated Python account trading, balance fetching, position management, martingale, grid trading, averaging down, executable leverage, optimization, and machine learning remain out of scope. Python-controlled MT5 execution is quarantined and not prop-compatible.

The Trial Risk-Free 10K account is the first MT5 platform testing environment. It is not approval for Surge 2 Step, Vanguard, or funded trading. Surge 2 Step 5K is rule-unverified and blocked until exact rules are reviewed and encoded. Vanguard 2K remains blocked until exact rules, trial evidence, source scan PASS, compile PASS, audit package ID, and explicit human approval metadata exist. Daily loss reset timezone must be confirmed from current Upcomers rules before challenge use; until confirmed, expose configurable `PropDayResetTimezone` and default conservatively. Exact Dynamic Risk Shield calculation must be verified before challenge presets are enabled.

## Session Definitions

- FX/gold/crypto New York session: `08:00-17:00 America/New_York`.
- London/New York overlap: `08:00-12:00 America/New_York`.
- U.S. index cash-session window: `09:30-16:00 America/New_York`.
- EST conversion: New York local time is UTC-05:00.
- EDT conversion: New York local time is UTC-04:00.
- Broker/server timestamps must be converted through an explicit broker timezone setting before session filtering.

Until a high-impact news filter exists, research and demo observation must avoid known high-impact news windows and low-liquidity periods such as rollover, late Friday, thin holidays, and abnormal spread conditions.

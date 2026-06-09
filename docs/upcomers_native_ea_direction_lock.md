# Upcomers Native EA Direction Lock

The final Upcomers prop-firm execution path is a native MQL5 Expert Advisor. Python-controlled MT5 execution is quarantined as legacy non-prop-compatible code and must not be used for Challenge, Verification, Funded, Surge 2 Step, Vanguard, or other prop deployment.

Python-controlled MT5 execution is quarantined as legacy, non-prop-compatible code. Python must not open, modify, close, check, or manage prop-account trades. Python remains useful for research, read-only data work, historical analysis, backtesting, validation, campaigns, reporting, source scanning, settings generation, log parsing, audit package export, and human review packages.

Trial Risk-Free account is the first MT5 platform testing environment. This refers to the Trial Risk-Free 10K account, and it is not approval for Surge 2 Step, Vanguard, or funded trading. Surge 2 Step 5K is rule-unverified and blocked until exact rules are reviewed and encoded. Vanguard 2K, Challenge, Verification, and Funded use remain blocked until exact rules, trial evidence, source scan PASS, compile PASS, audit package ID, and explicit human approval metadata exist.

Daily loss reset timezone must be confirmed from current Upcomers rules before challenge use. Until confirmed, the EA/settings layer must expose configurable `PropDayResetTimezone` and default conservatively.

Exact Dynamic Risk Shield calculation must be verified from current Upcomers rules before challenge presets are enabled.

No implementation phase may add grid, martingale, averaging down, HFT, arbitrage, copy trading, one-shot challenge passing, excessive order modification, hidden live-trading bypasses, or guaranteed-profit claims.

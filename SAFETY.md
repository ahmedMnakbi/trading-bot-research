# Safety

This project is non-live. It does not implement real exchange order placement, authenticated exchange clients, private account endpoints, leverage, short selling, optimization, or machine learning. It is not approved for real-money trading.

All trading-like behavior is simulated and intended for research, validation, paper trading, and review only, except for the Phase 13 native MQL5 Trial Risk-Free micro-execution path. That path is disabled by default and may be used only on the free Trial account after strict manual gates are set.

For Upcomers/prop-firm work, the final execution path must be a native MQL5 Expert Advisor. Python-controlled MT5 execution is quarantined as legacy non-prop-compatible code and must not be used for Challenge, Verification, Funded, Surge 2 Step, Vanguard, or any prop deployment.

The Trial Risk-Free 10K account is the first MT5 platform testing environment. It is not approval for Surge 2 Step, Vanguard, or funded trading. Surge 2 Step 5K is rule-unverified and blocked until its exact rules are reviewed and encoded. Vanguard 2K remains protected until exact rules, trial evidence, source scan PASS, compile PASS, audit package ID, and explicit human approval metadata exist.

Trial micro-execution requires `AccountProgram=TrialRiskFree`, `AccountStage=Trial`, `EnableTrading=true`, `EnableTrialExecution=true`, `EnablePropChallengeMode=false`, exact manual confirmation text `I_ACCEPT_TRIAL_RISK_FREE_EXECUTION_ONLY`, source scan PASS marker, EURUSD-only default symbols, one trade per day, one open position, required SL/TP, spread filter pass, and native MQL5 execution only. Surge 2 Step, Vanguard, Challenge, Verification, Funded, and live-money trading remain blocked.

Daily loss reset timezone must be confirmed from current Upcomers rules before challenge use. Until confirmed, the EA/settings layer must expose configurable `PropDayResetTimezone` and default conservatively. Exact Dynamic Risk Shield calculation must be verified from current Upcomers rules before challenge presets are enabled.

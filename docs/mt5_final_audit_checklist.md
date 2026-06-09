# MT5 Final Audit Checklist

The final Upcomers prop-firm execution path is a native MQL5 Expert Advisor. Python-controlled MT5 execution is quarantined as legacy non-prop-compatible code and must not be used for Challenge, Verification, Funded, Surge 2 Step, Vanguard, or other prop deployment.

## Audit Inputs

- Current code and configuration.
- MT5 symbol mapping and broker metadata report.
- Historical data quality reports.
- Backtests, out-of-sample validation, walk-forward validation, and campaigns.
- Trial MT5 platform testing evidence.
- Native EA source scan PASS and compile PASS evidence.
- Safety audit outputs.
- Decision logs, health logs, alerts, and incident replay artifacts.
- Audit package ID and explicit human approval metadata.

## Audit Questions

- Does the source reject live trading unless native EA gates, account stage, and approval metadata all pass?
- Are Python MT5 execution calls quarantined and absent from prop-compatible workflows?
- Do all strategies have objective, testable rules?
- Are session conversion and DST handling tested?
- Are spread, slippage, lot, stop-level, message-count, minimum-hold, and loss-limit gates enforced?
- Has the daily loss reset timezone been verified from current Upcomers rules, or does `PropDayResetTimezone` remain conservative and configurable?
- Has exact Dynamic Risk Shield behavior been verified before challenge presets?
- Are all decisions logged and auditable?
- Does the kill switch stop dangerous conditions?
- Are weak or rejected candidates clearly labeled?

No Challenge, Verification, Funded, Surge 2 Step, Vanguard, or tiny live pilot may proceed until exact account-program rules, Trial evidence, source scan PASS, compile PASS, Final Audit Agent review, audit package ID, and explicit human approval metadata exist.

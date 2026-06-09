# Known Limitations

Simulated fills are not real fills.

Fixture data is not market evidence.

Backtests can mislead.

Paper trading can mislead.

Strategies are fixed baselines, not proven profitable systems.

Live-money trading is not implemented.

The only real order path is the disabled-by-default native MQL5 Trial Risk-Free micro-execution module.

MT5 live-money trading, Surge 2 Step, Vanguard, Challenge, Verification, and Funded use are not approved.

Python MT5 execution is quarantined as legacy non-prop-compatible code and must not be used for Challenge, Verification, Funded, Surge 2 Step, Vanguard, or other prop deployment.

MT5 broker-specific risks are only partially modeled in native EA execution: broker-specific symbols, spread widening, slippage, stop-level restrictions, minimum lot and lot step constraints, news volatility, broker time zones, and demo/live differences still require manual review.

Daily loss reset timezone must be confirmed from current Upcomers rules before challenge use. Until confirmed, native EA settings must expose configurable `PropDayResetTimezone` and default conservatively.

Exact Dynamic Risk Shield calculation must be verified from current Upcomers rules before Challenge, Verification, or Funded presets are enabled.

# MT5 Safety Model

The final Upcomers prop-firm execution path is a native MQL5 Expert Advisor. Python-controlled MT5 execution is quarantined as legacy non-prop-compatible code and must not be used for Challenge, Verification, Funded, Surge 2 Step, Vanguard, or other prop deployment.

## Non-Live Boundary

Task 16 is read-only. The project may validate MT5 configuration, initialize a local terminal connection, inspect terminal status, and read symbol metadata. It must not place, check, modify, or prepare orders.

The following Python MT5 calls are prohibited in prop-compatible source code:

- `order_send`
- `order_check`
- `account_info`
- `positions_get`

They may appear in documentation, tests, scanner code, and explicitly quarantined legacy code only so the scanner can prove they are blocked elsewhere.

## MT5 Risks To Model Before Demo Or Live Use

- Broker-specific symbols: each broker can rename, suffix, hide, or route symbols differently.
- Spread widening: spreads can expand around rollover, session opens, illiquid periods, and news.
- Slippage: fills can differ materially from signal prices, especially on indices, gold, and crypto.
- Stop-level restrictions: brokers may require stops to be a minimum distance from current price.
- Minimum lot and lot step: volume must match broker constraints and can make small risk sizing impossible.
- News volatility: economic releases can invalidate normal spread and slippage assumptions.
- Broker time zones: candles and sessions can shift based on server time and daylight saving rules.
- Trial/funded differences: Trial execution, spreads, depth, and rejections can differ from funded conditions.

## Required Gates Before Any Live-Capable Design

1. Read-only MT5 discovery report.
2. Broker symbol mapping review.
3. Historical data quality review.
4. NY-session strategy research.
5. Demo-only observation.
6. Source scan PASS and MetaEditor compile PASS for the native EA.
7. Trial evidence package.
8. Final Audit Agent package ID.
9. Human approval metadata for any Challenge, Verification, Funded, Surge 2 Step, Vanguard, or protected account-program preset.

## Current Flags

- live trading: false
- execution enabled: false
- real orders allowed: false
- private account API allowed: false
- leverage: false
- shorting: false

## Absolute Prohibitions

Live account trading, real-money orders, Python MT5 execution, martingale, grid trading, averaging down, hidden safety bypasses, executable leverage, machine learning, and optimization are forbidden unless a later task explicitly approves a scoped native EA design.

Daily loss reset timezone must be confirmed from current Upcomers rules before challenge use. Until confirmed, expose configurable `PropDayResetTimezone` and default conservatively. Exact Dynamic Risk Shield calculation must be verified before challenge presets are enabled.

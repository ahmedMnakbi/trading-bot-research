# MT5 Strategy Research Plan

The final Upcomers prop-firm execution path is a native MQL5 Expert Advisor. Python-controlled MT5 execution is quarantined as legacy non-prop-compatible code and must not be used for Challenge, Verification, Funded, Surge 2 Step, Vanguard, or other prop deployment.

## Research Markets

- Forex: EURUSD, GBPUSD, USDJPY, and GBPJPY only if spread and volatility are safe.
- Gold: XAUUSD or the broker equivalent.
- Indices: NAS100/US100/USTEC, US500/SPX500, and US30/DJ30 broker equivalents.
- Crypto CFDs: BTCUSD/BTCUSDT and ETHUSD/ETHUSDT only if the MT5 broker supports them safely.

Broker-specific symbol names must be mapped from read-only metadata. The system must not assume one naming convention.

## Strategy Families

- Opening range breakout.
- VWAP trend continuation.
- Dynamic noise-band momentum with VWAP-based stop logic.
- London/New York overlap momentum.
- Volume/volatility expansion breakout.

Liquidity sweep and post-news strategies are deferred until converted into objective, testable rules. Discretionary vague logic is not accepted.

## Research Rules

All signals must be DST-aware and session-aware. Signals outside the configured session are invalid. Spread, volatility, session close, low-liquidity, and news-blackout filters must be modeled before demo observation.

Research may generate long and short simulation signals, but executable prop orders belong only in audited native MQL5 EA code after trial evidence and explicit human approval.

## Implemented Signal-Only Foundation

The initial New York-session strategy engine emits only objective research signals: `WAIT`, `SETUP_FORMING`, `ENTER_LONG`, `ENTER_SHORT`, `SKIP_SPREAD`, `SKIP_NEWS`, `EXIT`, and `SESSION_CLOSE`. The engine includes spread, news-blackout, configured-session, and session-close filters, but it does not place, check, or manage broker orders.

Daily loss reset timezone and exact Dynamic Risk Shield behavior must be verified from current Upcomers rules before Challenge, Verification, or Funded presets are enabled.

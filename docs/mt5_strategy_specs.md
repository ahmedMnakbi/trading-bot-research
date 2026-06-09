# MT5 Strategy Specs

Phase 9 strategy modules remain monitor-only signal generators. They may emit entry-intent records for audit and validation, but they cannot place orders, modify positions, trade Trial Risk-Free, Surge 2 Step, Vanguard, or any protected account, use prop credentials, log into MT5, or approve challenge use.

## Signal Result Contract

Every strategy decision must be built from closed bars only. Strategy state changes must not use the unfinished current candle. Entry intents are advisory records only and are refused by `TradeManager`.

Every signal record should include:

- strategy name
- symbol
- symbol class when available
- timeframe
- direction
- signal state
- server timestamp
- New York timestamp when conversion is available
- session tag
- reason codes
- suggested entry when applicable
- suggested stop-loss and take-profit when applicable
- minimum-hold-until timestamp
- spread/filter status
- volume type used when applicable
- monitor-only note

Entry intents must include a suggested stop-loss. If the stop-loss cannot be computed, the module must return `WAIT`, `SETUP_FORMING`, or `SKIP_DATA`.

## Session And Time Design

The EA must not assume broker server time equals New York time. `BrokerServerUtcOffsetMinutes` converts broker server timestamps to UTC, and `SessionManager` converts UTC to America/New_York using U.S. DST transition rules. The conversion handles server timestamp, UTC timestamp, and New York timestamp explicitly.

The user must still verify the broker server offset and symbol session behavior in MT5 before relying on session filters for Trial monitor-only observation. Historical broker-specific server-time changes are not inferred.

Required New York session windows:

- U.S. index cash session: 09:30-16:00 America/New_York.
- FX, gold, and crypto New York session: 08:00-17:00 America/New_York.
- London/New York overlap: 08:00-12:00 America/New_York.
- London/New York overlap reference range: 07:00-08:00 America/New_York.
- London/New York overlap late block: stop signaling near 11:55 America/New_York.

## Shared Prop-Firm Compatibility Guards

Strategies are designed for low-frequency monitor-only signals. Each strategy has a per-session signal cap and a duplicate-setup suppression guard. The default cap is one signal per strategy/session. Signals must not create repeated high-frequency alerts, forced one-sided bias, or sub-180-second intent assumptions.

Spread and news filters remain upstream gates in Phase 9. Strategy decisions carry `SPREAD_CHECKED_UPSTREAM` or an explicit skip reason so later implementation can trace why an intent did or did not form. Excessive or unknown spread returns `SKIP_SPREAD` before strategy evaluation.

## Opening Range Breakout

Opening Range Breakout uses M1 bars for range construction. `OpeningRangeMinutes` is converted to M1 bars, so minutes are not treated as raw bar count on other timeframes. Range construction is intended to start at the New York session start once the broker-to-New-York conversion is complete.

Default mode is `BreakThenRetest`. First-touch breakout behavior is not enabled.

Long intent requires:

- closed bar breaks above `ORBHigh + buffer`
- retest holds the broken level within `RetestWindowBars`
- confirmation closes back in the breakout direction

Short intent is symmetrical below `ORBLow - buffer`.

The module skips or waits when the opening range is too small or too large relative to closed-bar ATR. Suggested stop-loss is the lower of retest low and breakout bar low minus buffer for longs, or the higher of retest high and breakout bar high plus buffer for shorts. Suggested take-profit is an R-multiple placeholder until validated.

Reason codes include `ORB_RANGE_BUILT`, `ORB_WIDTH_OK`, `BREAK_CLOSE_OUTSIDE`, `RETEST_PASS`, `RETEST_FAIL`, `CLOSE_BACK_INSIDE`, `LATE_SIGNAL_BLOCK`, `SPREAD_BLOCK`, and `NEWS_BLOCK`.

## VWAP Trend Continuation

VWAP Trend Continuation uses closed M5 bars by default. It computes a session-reset VWAP design from typical price and tick volume. Session tagging now uses the Phase 9 broker-time to New York conversion, but broker offset validation remains required before Trial observation.

The strategy must not signal only because price is above or below VWAP. It requires:

- directional control relative to VWAP
- VWAP slope
- impulse leg away from VWAP
- controlled pullback near VWAP
- rejection candle confirmation

Long intent requires close above VWAP, positive VWAP slope, impulse at or above the configured ATR multiple, pullback near VWAP, and rejection close back above VWAP and above the prior bar high. Short intent is symmetrical. Flat or choppy VWAP behavior is blocked.

Suggested stop-loss is below the pullback low or VWAP buffer for longs, and above the pullback high or VWAP buffer for shorts.

Reason codes include `VWAP_BIAS_LONG`, `VWAP_BIAS_SHORT`, `VWAP_SLOPE_OK`, `PULLBACK_NEAR_VWAP`, `REJECTION_CLOSE_OK`, `IMPULSE_MISSING`, `VWAP_FLAT_BLOCK`, and `CHOP_BLOCK`.

## Dynamic Noise-Band Momentum Plus VWAP Stop

This is a derived engineered rule set, not a canonical proven strategy. It uses session VWAP as the band center. Band width is the maximum of an ATR multiple and a standard-deviation multiple.

Entry intent requires closed M5 band break, compression, range expansion, and normalized momentum. Suggested stop-loss is beyond the breakout bar or a VWAP buffer. The strategy remains monitor-only and emits no orders.

Reason codes include `BAND_COMPRESSED`, `BAND_BREAK_UP`, `BAND_BREAK_DOWN`, `MOMENTUM_OK`, `EXPANSION_OK`, `REENTRY_FAIL`, `WHIPSAW_BLOCK`, and `VWAP_FLAT_BLOCK`.

## London/New York Overlap Momentum

London/New York Overlap Momentum is FX/gold-focused by default. U.S. index CFDs are blocked by default unless a later approved phase adds an explicit opt-in.

The reference range is 07:00-08:00 New York, and the trading window is 08:00-12:00 New York. The module uses closed M5 bars, requires a range break plus trend alignment, and prefers break/retest confirmation. It hard-blocks late overlap signaling near 11:55 New York.

Reason codes include `OVERLAP_WINDOW_OK`, `REFERENCE_RANGE_BUILT`, `RANGE_BREAK_UP`, `RANGE_BREAK_DOWN`, `TREND_ALIGN_OK`, `RETEST_PASS`, `NEWS_BLOCK`, and `LATE_OVERLAP_BLOCK`.

## Volume/Volatility Expansion

Volume/Volatility Expansion builds a setup box from the last N closed bars, excluding the closed trigger bar. It requires contraction first, then a closed-bar break outside the box, range expansion relative to ATR, and volume expansion relative to median volume.

The module uses real volume when available and falls back to tick volume otherwise. Every decision records the volume type used. Suggested stop-loss is the opposite side of the setup box or an ATR buffer.

Reason codes include `SETUP_BOX_BUILT`, `CONTRACTION_OK`, `RANGE_EXPAND_OK`, `VOLUME_EXPAND_OK`, `BREAK_UP`, `BREAK_DOWN`, `REAL_VOLUME_USED`, `TICK_VOLUME_USED`, and `EXHAUSTION_BLOCK`.

## Approval Boundary

Source scan PASS and compile PASS are engineering checks only. They are not approval for Trial Risk-Free trading, Surge 2 Step, Vanguard, Challenge, Verification, Funded, or live use. Surge 2 Step and Vanguard remain blocked until exact rules, trial evidence, audit package, and explicit human approval metadata exist.

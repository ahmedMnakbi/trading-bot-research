# NY M15 Sweep Reclaim

## Status

Research/spec stage only. This strategy is not implemented, not approved for
live or protected account use, and not a profitability claim.

## Purpose

Fast-iteration research/demo strategy based on New York open liquidity sweep and
reclaim behavior. The idea is inspired by informal "CRT" descriptions, but this
spec avoids vague terminology and defines the rules mechanically from first
principles.

## Initial Market

- Initial implementation/testing market: `EURUSD`.
- Indices such as `NAS100` or `US500` may be considered later only after the
  first version is working, reviewed, and tested.

## Timeframes

- Trend timeframe: `H1`.
- Setup timeframe: `M15`.
- Entry timeframe: `M5`.

## Session

- New York open is explicitly defined as `09:30` America/New_York time.
- Default search window: `09:30` to `11:00` New York time.
- Use configurable time inputs where compatible with the existing project
  architecture.
- Maximum trades per day: `1`.

Time caution:

- Strategy session times are defined in America/New_York time.
- Implementation must convert NY session windows through the existing project
  session/time handling.
- Be careful with broker server time, `BrokerServerUtcOffsetMinutes`, and DST
  transitions.
- Do not hardcode broker-local time as if it were New York time.

## Closed-Bar Discipline

- H1 bar `[0]` is forbidden for trend decisions.
- Trend decisions must use only the last closed H1 bar.
- The M15 setup candle must be fully closed.
- M5 sweep, reclaim, and entry candles must be fully closed.
- No H1, M15, or M5 unclosed-bar decision is allowed.

## Trend Filter

Bullish trend:

- The last closed H1 candle close is above H1 EMA50.

Bearish trend:

- The last closed H1 candle close is below H1 EMA50.

No-trend behavior:

- If the last closed H1 close equals EMA50 or the EMA cannot be calculated, skip
  the day.

## Setup Candle

At or after `09:30` New York time, wait for the first fully closed M15 candle
inside the search window.

Bullish setup candle:

- H1 trend is bullish.
- First M15 candle closes bullish.
- Store that M15 candle high and low.

Bearish setup candle:

- H1 trend is bearish.
- First M15 candle closes bearish.
- Store that M15 candle high and low.

Important:

- If the first M15 candle disagrees with the H1 trend, skip the entire day.
- Do not keep searching for later M15 candles.
- If the M15 candle range is below `MinCRTRangePoints`, skip the day.

## Bearish Logic

State 1:

- H1 trend is bearish.
- The first NY M15 candle is bearish.
- Store the M15 high and low.

State 2:

- Wait for a later closed M5 candle to sweep above the stored M15 high by at
  least `MinSweepPoints`.
- Store the sweep high.

State 3:

- On a different later closed M5 candle, require close back below the stored M15
  high.
- This M5 candle is the reclaim/confirmation candle.
- Store the reclaim candle low.

State 4:

- Enter short intent when a later closed M5 candle closes below the reclaim
  candle low.

Stop loss:

- Above the sweep high plus `StopBufferPoints`.

Take profit:

- Fixed `TakeProfitR = 2.0` by default.

## Bullish Logic

State 1:

- H1 trend is bullish.
- The first NY M15 candle is bullish.
- Store the M15 high and low.

State 2:

- Wait for a later closed M5 candle to sweep below the stored M15 low by at
  least `MinSweepPoints`.
- Store the sweep low.

State 3:

- On a different later closed M5 candle, require close back above the stored M15
  low.
- This M5 candle is the reclaim/confirmation candle.
- Store the reclaim candle high.

State 4:

- Enter long intent when a later closed M5 candle closes above the reclaim
  candle high.

Stop loss:

- Below the sweep low minus `StopBufferPoints`.

Take profit:

- Fixed `TakeProfitR = 2.0` by default.

## State Machine

### States

- `IDLE`
- `CRT_CANDLE_SET`
- `SWEEP_DETECTED`
- `RECLAIM_CONFIRMED`
- `ENTRY_PENDING`
- `ENTER_LONG_INTENT`
- `ENTER_SHORT_INTENT`
- `TRADE_TAKEN`
- `CANCELLED`
- `SKIP_DAY`

### Transitions

`IDLE` to `CRT_CANDLE_SET`:

- The first fully closed M15 candle inside the NY search window agrees with the
  last closed H1 EMA50 trend filter.
- The M15 range is at least `MinCRTRangePoints`.

`IDLE` to `SKIP_DAY`:

- The last closed H1 close equals EMA50.
- EMA50 is unavailable or cannot be calculated.
- The first fully closed M15 candle disagrees with H1 trend.
- The first M15 candle range is below `MinCRTRangePoints`.
- No fully closed M15 candle is available before the search window ends.

`CRT_CANDLE_SET` to `SWEEP_DETECTED`:

- Bearish path: a later closed M5 candle sweeps above the stored M15 high by at
  least `MinSweepPoints`.
- Bullish path: a later closed M5 candle sweeps below the stored M15 low by at
  least `MinSweepPoints`.

`SWEEP_DETECTED` to `RECLAIM_CONFIRMED`:

- Bearish path: a different later closed M5 candle closes back below the stored
  M15 high.
- Bullish path: a different later closed M5 candle closes back above the stored
  M15 low.

`RECLAIM_CONFIRMED` to `ENTRY_PENDING`:

- The reclaim candle has closed and the breakout trigger level is stored.

`ENTRY_PENDING` to `ENTER_SHORT_INTENT`:

- Bearish path: a later closed M5 candle closes below the reclaim candle low.

`ENTRY_PENDING` to `ENTER_LONG_INTENT`:

- Bullish path: a later closed M5 candle closes above the reclaim candle high.

`ENTER_LONG_INTENT` or `ENTER_SHORT_INTENT` to `TRADE_TAKEN`:

- A StrategyBase-compatible signal intent has been emitted for the day.
- Execution handling remains outside this strategy spec.

Any active state to `CANCELLED`:

- The `11:00` NY window end is reached before an entry intent has fired.
- More than `MaxBarsAfterSweep` closed M5 bars pass after sweep detection
  without reclaim confirmation.
- Required candle, EMA, spread/session, or symbol data is unavailable.
- Stop loss or take profit cannot be computed with valid positive distance.

`CANCELLED` to `SKIP_DAY`:

- The strategy is done for the session and must not re-enter that day.

`TRADE_TAKEN` to `SKIP_DAY`:

- The strategy has emitted its one allowed intent for the day.

## Default Parameters

These are defaults for initial testing, not optimized values.

| Parameter | Default |
| --- | --- |
| `NYOpenHour` | `9` |
| `NYOpenMinute` | `30` |
| `NYWindowEndHour` | `11` |
| `NYWindowEndMinute` | `0` |
| `EMA_Period` | `50` |
| `MinCRTRangePoints` | `100` |
| `MinSweepPoints` | `20` |
| `StopBufferPoints` | `50` |
| `TakeProfitR` | `2.0` |
| `MaxBarsAfterSweep` | `12` |
| `MaxTradesPerDay` | `1` |

## Signal Output

The implementation should emit StrategyBase-compatible signal intent only:

- `WAIT` while no valid condition exists.
- `SETUP_FORMING` while the setup is valid but incomplete.
- `ENTER_LONG_INTENT` only after the bullish entry trigger closes.
- `ENTER_SHORT_INTENT` only after the bearish entry trigger closes.
- `SKIP_DAY` or equivalent reason codes after cancellation.

The strategy must not place orders and must not require execution module
changes.

## Prohibited Behavior

- No grid.
- No martingale.
- No averaging down.
- No same-signal revenge re-entry.
- No live/protected account use.
- No same-candle sweep and reclaim for version 1.
- No H1/M15/M5 unclosed-bar decisions.
- No parameter optimization without explicit approval.

## Acceptance Criteria Before Implementation

- Spec is committed.
- Claude Chat critique has been incorporated.
- Strategy uses closed bars only.
- No execution module changes are required.
- Implementation can emit StrategyBase-compatible signal intent.
- State transitions are deterministic.
- Source scan must pass after implementation.
- Compile check should pass where MetaEditor is available.
- Focused pytest suite should pass.

## Research Notes

Manual MT5 Strategy Tester results may be reported using
`docs/manual_backtest_result_template.md` during fast iteration. Full Strategy
Tester evidence packaging remains optional for routine exploration, but should
be used before treating this as a serious candidate.

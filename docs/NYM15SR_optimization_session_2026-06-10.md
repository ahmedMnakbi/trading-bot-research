# NYM15SR NACUSD.c Research Session - 2026-06-10

This note is research-only Strategy Tester context. It does not approve Trial,
live, protected-account, Surge 2 Step, Vanguard, Challenge, Verification, or
Funded execution.

## Baseline Context

- EA: `UpcomersNYSessionPropBot`
- Strategy: `STRATEGY_NY_M15_SWEEP_RECLAIM`
- Symbol: `NACUSD.c`
- Timeframe: `M5`
- Test period reported by user: 2026-04-01 to 2026-06-01
- Starting balance reported by user: 10000.00

## Fixed Tester Gate

The first NACUSD.c run generated NYM15SR entry intents, but tester orders were
blocked by an execution-layer `AllowedSymbols` gate. Current `main` includes the
tester-only fix in commit `c31c12e`, so the tester order path now accepts only
the approved research symbols:

- `EURUSD`
- `NACUSD.c`
- `SPCUSD.c`

Trial, live, and protected-account gates remain unchanged.

## User-Reported Baseline After Gate Fix

After recompiling with the tester gate fix, the user-reported NACUSD.c baseline
showed:

- 6 entry intents
- 5 tester orders sent
- 1 signal blocked by `PositionCapsTotal=1` while a previous tester position was
  still open
- all entries were long
- final balance approximately `10003.09`

The tester path intentionally normalized volume to the minimum lot, so this is
not a profitability claim and should not be scaled into live expectations.

## Bottleneck Diagnosis

Parameter-only tests reported by the user had identical results:

| Run | MinSweepPoints | Window End | MaxBarsAfterSweep | Signals | Balance |
| --- | ---: | --- | ---: | ---: | ---: |
| Baseline | 500 | 11:00 NY | 12 | 6 | 10003.09 |
| Moderate | 250 | 11:30 NY | 18 | 6 | 10003.09 |
| Aggressive | 100 | 12:00 NY | 24 | 6 | 10003.09 |

The main observed bottleneck was `NYM15SR_M15_DISAGREES_WITH_H1`: many sessions
were skipped before sweep, reclaim, window, or range parameters could matter.
For NACUSD.c during the reported period, the first NY M15 candle often
disagreed with the H1 EMA trend during an overall strong uptrend.

## New Mechanical Variant

Branch `research/nacusd-nym15sr-m15-direction-variant` adds an opt-in research
variant:

- New EA input: `NYM15SRRequireM15DirectionAgreement`
- Default: `true`
- Baseline behavior: unchanged
- Variant behavior: set to `false` so the first closed NY M15 candle can be used
  even when its candle direction disagrees with the H1 EMA trend
- Trade direction still comes from the H1 EMA trend
- Sweep, reclaim, entry, stop, take-profit, closed-bar discipline, one-trade
  daily cap, and tester safety gates remain unchanged

Generated variant preset:

`data/processed/ea_settings/strategy_tester_nacusd_c_m5_ny_m15_sweep_reclaim_relaxed_m15_direction.set`

Next manual MT5 Strategy Tester comparison should keep the same symbol,
timeframe, broker, model, spread behavior, and date range as the baseline:

- Expert: `UpcomersNYSessionPropBot`
- Symbol: `NACUSD.c`
- Timeframe: `M5`
- Date range: 2026-04-01 to 2026-06-01
- Baseline preset:
  `data/processed/ea_settings/strategy_tester_nacusd_c_m5_ny_m15_sweep_reclaim.set`
- Variant preset:
  `data/processed/ea_settings/strategy_tester_nacusd_c_m5_ny_m15_sweep_reclaim_relaxed_m15_direction.set`

Record results with `docs/manual_backtest_result_template.md`. Compare at least
entry intents, tester orders attempted, trades, net profit, drawdown, profit
factor, win rate, `NYM15SR_M15_DISAGREES_WITH_H1`, `NYM15SR_WINDOW_EXPIRED`,
and any tester gate failures.

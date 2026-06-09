# Strategy Validation Metrics

Phase 9 does not approve trading. These metrics define what later research and Strategy Tester evidence must report before any Trial monitor-only observation or protected-stage discussion.

Required metrics:

- net profit factor
- expectancy in R
- max drawdown at 0.25% risk
- trade frequency per day
- average and median hold time
- sub-180-second events
- spread sensitivity
- long/short balance
- session concentration
- repeated-signal density
- broker-time conversion mismatches
- spread-block rate
- throttle-skip rate
- monitor evaluations versus trade intents versus refused actions versus actual server messages

## Interpretation

Profit factor and expectancy must be evaluated after costs and realistic spread assumptions. Drawdown must be measured at the default `RiskPerTradePct=0.25`, not at inflated risk. Trade frequency, repeated-signal density, throttle-skip rate, spread-block rate, and sub-180-second events are prop-compatibility checks, not optimization targets.

## Required Evidence Before Trial Observation

Before any Trial Risk-Free observation, the project still needs:

- broker server UTC offset validation against current MT5 server time, UTC, and America/New_York
- DST-aware broker server time to New York conversion validation
- broker symbol session validation for index, FX/gold/crypto, and London/New York overlap windows
- closed-bar-only strategy evaluation confirmation from logs
- ORB minutes-to-bars handling validation
- OnTick/OnTimer throttling validation
- spread gate implementation evidence against live broker symbol metadata
- trade/message counter semantics evidence
- exact Surge 2 Step rule review before any Surge use
- exact Vanguard rule review before any Vanguard use

Surge 2 Step and Vanguard remain blocked. Strategy Tester evidence, real monitor-only EA logs, trial evidence, final audit package review, and explicit human approval metadata are still required before protected-stage use.

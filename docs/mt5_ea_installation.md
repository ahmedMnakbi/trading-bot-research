# MT5 EA Installation

Phase 13 prepares a manual install for the Upcomers Trial Risk-Free account. Execution remains disabled by default. The isolated Trial micro-execution path is for the free Trial account only and does not approve Surge 2 Step, Vanguard, Challenge, Verification, Funded, or live use.

## Manual Copy

Open MT5, then use `File > Open Data Folder`. Copy these repo files into the matching MT5 data-folder locations:

- `mql5/Experts/UpcomersNYSessionPropBot/UpcomersNYSessionPropBot.mq5` to `MQL5/Experts/UpcomersNYSessionPropBot/UpcomersNYSessionPropBot.mq5`
- `mql5/Include/UpcomersNYSessionPropBot/*.mqh` to `MQL5/Include/UpcomersNYSessionPropBot/*.mqh`

Do not place account passwords, investor passwords, API keys, or prop credentials in the repo, in `.set` files, or in evidence packages.

## Compile

Open MetaEditor manually from MT5 or Windows. Compile `MQL5/Experts/UpcomersNYSessionPropBot/UpcomersNYSessionPropBot.mq5`.

The compile result is only syntax evidence. It is not approval to trade.

## Safe Settings

Generate the safe Trial monitor-only settings from the repo:

```powershell
python scripts/generate_ea_settings.py --account-program TrialRiskFree --stage Trial
```

Import the generated `.set` file in MT5 EA inputs. Verify these inputs before attaching:

- `EnableTrading=false`
- `EnableTrialExecution=false`
- `EnablePropChallengeMode=false`
- `AccountProgram=TrialRiskFree`
- `AccountStage=Trial` or `MonitorOnly`
- `UseSpreadFilter=true`
- `SpreadUnknownBlocksTrading=true`
- `EvaluationMode=OnNewClosedBar`

Update `BrokerServerUtcOffsetMinutes` only after completing broker time verification.

## Attach Boundary

Attach the EA only to the Trial Risk-Free account first, and only for monitor/logging observation. Do not attach to Surge 2 Step or Vanguard.

MT5 may require Algo Trading to be enabled for EA timer/logging callbacks. For monitor-only observation, it may be enabled only while `EnableTrading=false` and `EnableTrialExecution=false`. If any input shows trading enabled outside the separately approved Trial micro-execution workflow, remove the EA immediately.

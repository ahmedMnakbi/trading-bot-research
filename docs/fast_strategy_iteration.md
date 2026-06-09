# Fast Strategy Iteration

This workflow supports faster manual strategy research while preserving the
project safety boundaries. It is for research only and does not approve Trial,
Surge 2 Step, Vanguard, Challenge, Verification, Funded, or live-money
execution.

## Fast Loop

1. ChatGPT drafts a strategy concept or specification.
2. Claude Chat critiques risk, architecture, signal contracts, and unsafe
   assumptions.
3. The user approves, rejects, or revises the concept.
4. Claude Code or Codex implements only from an approved committed spec.
5. The user runs MT5 Strategy Tester locally.
6. The user manually reports results using
   [manual_backtest_result_template.md](manual_backtest_result_template.md).
7. ChatGPT and Claude review the structured results.
8. The user decides the next action: reject, revise, expand the test, or mark as
   a Trial-sandbox candidate.

Manual reporting is allowed so every exploratory Strategy Tester run does not
need a full evidence package. The tradeoff is that manually reported results are
informal research notes until raw tester reports/logs are packaged.

## Minimum Discipline

Each manual result should include the strategy name, symbol, timeframe, date
range, model/spread, settings file, net profit, drawdown, profit factor, trade
count, win rate, and bad-behavior notes. Results without these fields are useful
as conversation context, but they should not drive implementation decisions.

Use one result template per run. Keep the strategy, symbol, timeframe, and date
range stable when comparing strategies. Do not compare a clean ORB run against a
VWAP run that used different date ranges, spreads, or settings unless the
difference is clearly documented.

## Safety Gates

Free Trial or demo testing may be considered only after a strategy has:

- an approved committed spec
- a clean MQL5 source scan
- a successful compile
- at least basic manual Strategy Tester results

Full evidence packaging remains optional for routine iteration, but it should be
used for serious candidate strategies before any real/protected execution is
even considered.

Real-money and protected-account execution remain blocked unless explicitly
approved in a later phase. Surge 2 Step, Vanguard, Challenge, Verification, and
Funded use remain blocked.

## What This Does Not Permit

This workflow does not permit:

- live or protected account execution
- strategy parameter optimization without explicit approval
- strategy logic edits without an approved committed spec
- execution logic edits
- raw MT5 exports or account-sensitive artifacts committed to git
- credentials, broker configs, tokens, or account exports in the repo

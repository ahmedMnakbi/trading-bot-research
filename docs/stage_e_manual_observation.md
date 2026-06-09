# Stage E Manual Portfolio Paper Observation

This routine is for the existing non-live portfolio paper run:

- Portfolio paper run: `portfolio_paper_20260531T000734_70ff121c`
- Config: `config/stage_e_portfolio_paper.yaml`
- Exchange/cache: `binance`
- Symbols: `BTC/USDT`, `ETH/USDT`
- Timeframe: `4h`
- Strategies: `donchian_breakout` for both symbols
- Campaign reference: `campaign_20260530T235504_f117ea13`

## Safety Boundary

- Do not enable live trading.
- Do not use API keys.
- Do not use authenticated exchange APIs.
- Do not place real orders.
- Do not fetch balances.
- Do not use private or account endpoints.
- Do not add optimization or machine learning.
- Do not leave an unattended infinite process running.

## Manual Check Routine

Run this routine once after a newly closed 4h candle is available in the Binance cache. If the cache has not advanced beyond `last_processed_candle_by_symbol`, do not force a run.

1. Run one bounded portfolio paper check:

```powershell
& 'C:\Users\Mega pc\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m trading_bot run-portfolio-paper --config config/stage_e_portfolio_paper.yaml --exchange binance --symbols 'BTC/USDT,ETH/USDT' --timeframe 4h --campaign-run-id campaign_20260530T235504_f117ea13 --max-iterations 1
```

Use `--max-iterations 2` only when intentionally checking duplicate-candle handling after one normal pass.

2. Generate the portfolio report:

```powershell
& 'C:\Users\Mega pc\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m trading_bot report-portfolio-paper --config config/stage_e_portfolio_paper.yaml --portfolio-paper-run-id portfolio_paper_20260531T000734_70ff121c
```

3. Run the safety audit:

```powershell
& 'C:\Users\Mega pc\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m trading_bot run-safety-audit --config config/stage_e_portfolio_paper.yaml
```

4. Index artifacts:

```powershell
& 'C:\Users\Mega pc\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m trading_bot index-artifacts
```

## Observation Log Fields

Record these after each manual check:

- Check timestamp
- Last processed candle per symbol
- New decisions
- Orders
- Trades
- Open positions
- Equity
- Exposure
- Health events by code
- Alerts by code
- Kill switch state
- Report path
- Audit path

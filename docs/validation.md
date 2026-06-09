# Validation

Task 5 adds local out-of-sample and walk-forward validation for fixed-parameter strategies. It does not optimize parameters, call exchanges, paper trade, or make profitability claims.

## Why One Backtest Is Not Enough

A single historical period can flatter a strategy by coincidence. Validation checks whether behavior changes across later data, rolling windows, benchmarks, and simple market regimes.

## Chronological Train/Test Split

The static split uses the first configured percentage as train data and the last configured percentage as test data. Chronological order is preserved because market data is a time series.

## Why Random Splits Are Forbidden

Random splits leak future market regimes into training samples and destroy time ordering. That can hide look-ahead bias and make results appear more stable than they are.

## Walk-Forward Validation

Walk-forward validation evaluates fixed parameters over rolling train/test windows. The train window is reported for context only; it is not used to tune anything.

## Indicator Warmup Context

Validation test windows may include earlier historical candles as indicator warmup context. The simulated account still starts flat at the test boundary, orders can only fill on test-period candles, and equity/trade metrics are recorded only from the test period forward. This lets slow indicators such as EMA(200) behave normally in a 125-bar test window without giving the strategy access to future candles or counting pre-test performance.

## Fixed Parameters

Parameters remain fixed at this stage so the project can audit strategy behavior without overfitting. Optimization is intentionally excluded.

## Benchmark Comparison

Each configured strategy is compared with `noop` and `buy_and_hold`. Positive return alone is not enough; comparison includes drawdown, profit factor, fees, slippage, and trade count.

## Regime Tagging

Regime tagging uses a moving average and rolling volatility to label candles as uptrend, downtrend, range, high volatility, low volatility, or unknown. It is diagnostic, not predictive.

## Warning Flags

Warnings are audit signals, not test failures. They highlight zero trades, too few trades, test return collapse, worse test drawdown, buy-and-hold underperformance, high drawdown, unstable profit factor, or missing regime data.

## Not Profit Claims

Validation results describe historical simulation behavior only. They are not investment advice and do not imply future profitability.

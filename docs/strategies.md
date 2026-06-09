# Strategies

Task 4 adds fixed-parameter baseline strategies for simulation correctness. These strategies are transparent examples, not profitability claims.

## Purpose

The baseline strategies exercise stop-loss-aware trade intents, fixed fractional position sizing, simulated fills, and auditable result artifacts before any parameter search exists.

## Donchian Breakout

`donchian_breakout` is long-only. It compares the current close against the previous completed Donchian upper channel. If price breaks out and ATR is available, it emits a BUY intent with an ATR-based stop. It exits when price closes below the previous completed Donchian middle channel or when the simulator hits the stop or take-profit.

## EMA Trend

`ema_trend` is long-only. It requires the fast EMA above the slow EMA and price above the fast EMA, with a simple cross/regime-change condition. It emits a BUY intent with an ATR stop and exits if the fast EMA falls below the slow EMA, price closes below the fast EMA, or the simulator hits the stop or take-profit.

## ATR Stop

ATR is a rolling mean of true range. Stops are placed below the reference close using `atr_stop_multiple`. If ATR is unavailable, zero, or invalid, strategies hold.

## Fixed Fractional Risk

Position sizing risks a fixed fraction of equity per trade:

```text
risk_amount = equity * risk_per_trade_pct / 100
quantity = risk_amount / (entry_price - stop_loss)
```

Sizing is reduced if cash is insufficient, and trades are rejected if stop distance is too small, too large, missing, or above the entry price.

## No Optimization

Optimization is intentionally excluded. Tuning parameters before the simulator and risk controls are proven would encourage overfitting and false confidence.

## Known Failure Modes

- False breakouts
- Whipsaw
- Gap/slippage risk
- Trend regime changes
- Overfitting risk if parameters are tuned too aggressively

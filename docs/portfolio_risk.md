# Portfolio Risk

Portfolio risk matters more than single-trade risk because multiple individually acceptable entries can combine into unsafe exposure, shared-cash conflicts, correlated drawdowns, or duplicated strategy bets.

## Max Open Positions

`max_open_positions` caps the number of simultaneous open portfolio positions.

## Max Total Exposure

`max_total_exposure_pct` caps total gross exposure as a percentage of portfolio equity.

## Max Symbol Exposure

`max_symbol_exposure_pct` caps exposure in any one symbol.

## Max Strategy Exposure

`max_strategy_exposure_pct` caps combined exposure assigned to one strategy.

## Min Cash Rule

`min_cash_pct` rejects entries that would leave too little cash after simulated notional and fees.

## Daily And Weekly Loss Limits

Daily and weekly loss settings reject new entries when portfolio equity loss from starting equity breaches configured thresholds.

## Drawdown Kill Switch

`max_drawdown_pct` activates the portfolio kill switch when equity drawdown breaches the configured limit.

## Correlation Warnings And Rejections

The engine warns when a candidate entry is correlated with existing open positions beyond `correlation_warning_threshold`. If `reject_correlated_entries` is true, the candidate is rejected instead of only warned.

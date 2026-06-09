# Symbol Session Verification

Broker symbol names and sessions differ. Verify symbols manually on the Trial Risk-Free account before Trial monitor-only observation.

## Symbols To Check

- forex symbols, including major pairs with broker suffixes or prefixes.
- XAUUSD or gold equivalents.
- NAS, US100, US500, US30, SPX, USTEC, or other U.S. index CFD equivalents.
- BTC, ETH, or crypto CFD equivalents if present.

## Session Checklist

1. Record the exact broker symbol name.
2. Confirm whether the symbol is visible and tradable in Market Watch.
3. Observe whether ticks arrive inside the expected New York window.
4. Confirm U.S. index cash behavior around 09:30-16:00 America/New_York.
5. Confirm FX/gold/crypto behavior around 08:00-17:00 America/New_York.
6. Confirm London/New York overlap behavior around 08:00-12:00 America/New_York.
7. Record screenshots or notes for each symbol class.

## Spread Checklist

1. Observe spread in MT5 Market Watch.
2. Compare it to EA log messages for `SPREAD_OK`, `SPREAD_BLOCK`, or `SPREAD_UNKNOWN`.
3. Keep `UseSpreadFilter=true`.
4. Keep `SpreadUnknownBlocksTrading=true`.
5. Adjust `MaxSpreadPoints` only after documenting normal spread ranges.

This verification is monitor-only. It does not approve Trial trading, Surge 2 Step, Vanguard, or any funded use.

# MT5 Symbol Mapping

## Problem

MT5 symbols are broker-specific. The same market can appear as `EURUSD`, `EURUSD.a`, `XAUUSD`, `GOLD`, `US30.cash`, `NAS100`, `BTCUSD`, or other broker-defined names. A safe bot must not assume one universal symbol list.

## Read-Only Metadata Used

The Task 16 model stores only planning-safe symbol metadata:

- name
- path
- description
- visibility
- trade mode code
- digits
- point size
- current spread value if exposed by metadata
- minimum volume
- volume step
- stop-level restriction
- asset class label

## Initial Categories

- forex: major and minor currency pairs such as EURUSD, GBPUSD, USDJPY.
- gold: XAUUSD, GOLD, and related broker aliases.
- index: US30, NAS100, US500, GER40, DAX, UK100, JP225, and similar broker aliases.
- crypto: BTCUSD, BTCUSDT, ETHUSD, ETHUSDT, XBT, SOL, XRP, LTC, and similar aliases.
- commodity: XAG, SILVER, OIL, WTI, BRENT, NGAS, COPPER, and similar aliases.
- unknown: anything that cannot be categorized safely.

Unknown symbols stay unknown until explicitly reviewed. They should not be forced into a tradable category.

## Mapping Rules

Broker symbol mapping must preserve the raw MT5 symbol name. A future strategy label such as `gold` or `nasdaq_index` can map to one or more broker symbols only after the symbol metadata and trading constraints are reviewed.

Mappings should include broker time zone notes, trading session notes, spread expectations, stop-level restrictions, and lot constraints before any demo observation is considered.

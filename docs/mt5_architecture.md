# MT5 Architecture

The final Upcomers prop-firm execution path is a native MQL5 Expert Advisor. Python-controlled MT5 execution is quarantined as legacy non-prop-compatible code and must not be used for Challenge, Verification, Funded, Surge 2 Step, Vanguard, or other prop deployment.

## Layers

1. Configuration: `config/mt5_readonly.yaml` defines read-only mode, disabled execution, disabled real orders, disabled private account access, and NY-session defaults.
2. Safety model: MT5-specific scanners reject execution and account function usage outside explicit documentation and tests.
3. MT5 connector: `Mt5ReadOnlyConnector` may initialize a local terminal only in read-only mode and can request terminal status plus symbol metadata.
4. Symbol model: broker metadata is normalized into `Mt5SymbolInfo` with asset class labels such as forex, gold, index, crypto, commodity, and unknown.
5. Data layer: `Mt5RatesProvider` supports read-only historical range fetches and bounded recent-rate polling, with cache and inspection tooling.
6. Research layer: NY-session strategies consume normalized MT5 data for signal-only research, backtesting, validation, and campaigns.
7. Monitor layer: bounded MT5 monitoring can consume cached or read-only recent rates and track internal state without Python broker execution.
8. Native EA layer: future MQL5 code owns any approved Trial and later prop execution after scans, compile checks, audit package, trial evidence, and human approval.

The long-term architecture targets an MT5 New York-session multi-market native EA. Each future layer must remain safety-gated: read-only discovery before data ingestion, data quality before strategy research, strategy evidence before monitor-only Trial Risk-Free testing, source scan and compile checks before any EA execution, and Final Audit Agent review plus human approval before any Surge 2 Step, Vanguard, or funded use.

## Time And Session Handling

- FX/gold/crypto New York session: `08:00-17:00 America/New_York`.
- London/New York overlap: `08:00-12:00 America/New_York`.
- U.S. index cash-session window: `09:30-16:00 America/New_York`.
- EST conversion: New York local time is UTC-05:00.
- EDT conversion: New York local time is UTC-04:00.
- Broker/server timestamps must be converted through an explicit broker timezone setting before session filtering.

## Allowed In Current Python Support

- Validate MT5 read-only configuration.
- Import the MetaTrader5 package if installed.
- Initialize the local terminal connection when the config remains read-only.
- Read terminal status.
- Read symbol metadata.
- Categorize symbols for planning.

## Prohibited In Python Prop Workflows

- No Python `order_send`.
- No Python `order_check`.
- No Python `account_info`.
- No Python `positions_get`.
- No balance reads.
- No real orders.
- No live trading.
- No leverage or shorting enablement.
- No strategy optimization or ML.

## Operational Flow

```text
CLI -> MT5 config validation -> source safety scan -> optional terminal init
    -> terminal status -> symbol metadata -> symbol categorization -> console summary
```

Secrets are not required for this stage and must never be printed. Daily loss reset timezone and exact Dynamic Risk Shield calculation must be verified from current Upcomers rules before challenge presets are enabled.

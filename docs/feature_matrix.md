# Feature Matrix

| Feature | Status | Mode | Live Trading? | Notes |
|---|---|---|---|---|
| Config validation | Implemented | Local | No | Safety gates enforced |
| OHLCV ingestion | Implemented | Public data | No | Public read-only data only |
| Data inspection | Implemented | Local | No | Cached data checks |
| Backtesting | Implemented | Local simulation | No | Simulated fills |
| Strategies | Implemented | Fixed parameter | No | Baselines only |
| Validation | Implemented | Local | No | Out-of-sample and walk-forward |
| Campaigns | Implemented | Local | No | Fixed-parameter campaigns |
| Single-symbol paper trading | Implemented | Simulated | No | Simulated orders only |
| Portfolio paper trading | Implemented | Simulated | No | Shared simulated cash |
| Paper reports | Implemented | Local | No | Review artifacts |
| Portfolio reports | Implemented | Local | No | Review artifacts |
| Failure injection | Implemented | Simulated | No | Local faults only |
| Incident replay | Implemented | Local | No | Artifact replay |
| Safety audit | Implemented | Local | No | Prohibited-path checks |
| Artifact integrity | Implemented | Local | No | Manifests and hashes |
| Operator profiles | Implemented | Local | No | Unsafe overlays rejected |
| Run registry | Implemented | Local | No | Artifact discovery |
| Archiving | Implemented | Local | No | Excludes sensitive files |
| CI checks | Implemented | CI/local | No | No secrets required |
| Real exchange order placement | Not implemented / Forbidden | None | No | Forbidden |
| Authenticated exchange client | Not implemented / Forbidden | None | No | Forbidden |
| Live trading | Not implemented and not approved | None | No | Forbidden |
| Leverage | Not implemented / Forbidden | None | No | Forbidden |
| Short selling | Not implemented / Forbidden | None | No | Forbidden |
| Optimization | Not implemented / Forbidden | None | No | Forbidden |
| Machine learning | Not implemented / Forbidden | None | No | Forbidden |
| MT5 read-only discovery | Implemented | Read-only local terminal | No | Terminal status and symbol metadata only |
| MT5 transformation roadmap | Implemented | Documentation/config | No | Planning package only |
| MT5 historical data ingestion | Implemented | Read-only local terminal/cache | No | Historical range fetches and recent-rate polling are read-only |
| MT5 NY-session strategies | Implemented | Signal-only research | No | Opening range, VWAP, noise-band, overlap momentum, and volume/volatility signals |
| MT5 cached-data backtesting | Implemented | Local simulation | No | Research-only NY-session signals with MT5 market constraints |
| MT5 validation and walk-forward | Implemented | Local simulation | No | Static split and walk-forward over cached MT5 rates |
| MT5 strategy campaigns | Implemented | Local simulation | No | Candidate labels are research review signals only |
| Python MT5 execution | Quarantined / Non-prop-compatible | Legacy only | No | Must not be imported by prop-compatible workflows |
| MT5 monitor | Implemented | Bounded monitor-only | No live | Cached or read-only recent-rate checks with decisions, health events, internal protective exits, and state; no broker execution |
| Native MQL5 EA source | Trial micro-execution source exists / Disabled by default | Native EA source | Trial Risk-Free only when manually armed | Source scan and compile supported; order call isolated to TrialExecution |
| Native MQL5 EA execution | Trial Risk-Free micro-execution gated / Protected use blocked | Native EA | Trial Risk-Free only when manually armed | Not Surge, Vanguard, Challenge, Verification, Funded, or live-money approval |
| MT5 live execution | Not implemented / Forbidden | None | No | Forbidden and not approved |
| MT5 live trading | Not implemented / Forbidden | None | No | Forbidden and not approved |
| MT5 order placement | Isolated native TrialExecution only / Disabled by default | Native EA | Trial Risk-Free only when manually armed | No Python order execution; no protected-account approval |
| MT5 account reads | Not implemented / Forbidden | None | No | Forbidden |
| MT5 position reads | Not implemented / Forbidden | None | No | Forbidden |
| MT5 balance fetching | Not implemented / Forbidden | None | No | Forbidden |

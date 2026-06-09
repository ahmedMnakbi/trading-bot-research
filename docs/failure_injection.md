# Failure Injection

Failure injection exists to prove the simulated bot fails safely under dangerous local conditions before any real execution connector is considered.

Run one scenario:

```bash
python -m trading_bot run-failure-scenarios --config config/default.yaml --scenario stale_data --target portfolio-paper
```

Run all supported scenarios:

```bash
python -m trading_bot run-failure-scenarios --config config/default.yaml --scenario all --target portfolio-paper
```

Supported scenarios simulate stale data, missing candles, duplicate candles, corrupted state, strategy exceptions, simulated order rejection, state write failure, and interrupted runs. Expected safe behavior is to emit health events and alerts, skip affected symbols where possible, avoid duplicate orders, activate the kill switch where thresholds are exceeded, and write local artifacts for review.

Failure injection is disabled by default in normal configuration and only runs when explicitly invoked. These tests are simulated only: they do not call exchanges, do not place orders, do not require account credentials, and do not approve live trading.

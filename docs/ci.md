# CI Safety Gates

The canonical cross-platform local check is:

```bash
python scripts/check_all.py
```

For a narrower safety-only pass, run:

```bash
python scripts/check_safety.py
```

Use deterministic fixture data when smoke runs need cached OHLCV without internet access:

```bash
python scripts/generate_fixture_data.py
```

Generated artifacts can be cleaned with:

```bash
python scripts/clean_artifacts.py --dry-run
python scripts/clean_artifacts.py
```

Raw cached OHLCV is preserved by default. It is removed only when explicitly requested:

```bash
python scripts/clean_artifacts.py --include-raw-data
```

## What CI Runs

GitHub Actions runs separate jobs for linting, tests, configuration validation, and safety audit:

- `python -m ruff check .`
- `python -m pytest`
- `python -m trading_bot validate-config --config config/default.yaml`
- `python -m trading_bot run-safety-audit --config config/default.yaml`

The workflow generates local fixture data where cached data is useful. It must not require exchange API keys, private credentials, or any external trading account.

## No Secrets And No Real Exchange Calls

CI is intentionally designed around local code, local config, and deterministic fixture data. It must not call real exchange APIs, must not use private secrets, and must not depend on account state. A passing CI run is a review gate only; it is not approval for live trading.

## Handling Safety Audit Failures

Treat a safety audit failure as a release blocker. Fix the underlying unsafe code, config, environment, artifact, or governance issue, then rerun `python scripts/check_safety.py`. Do not bypass the audit to merge trading-related changes.

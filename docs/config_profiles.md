# Config Profiles

Profiles are YAML overlays loaded from `config/profiles/{profile}.yaml` and merged over `config/default.yaml`.

Example:

```bash
python -m trading_bot validate-config --config config/default.yaml --profile research
```

Profiles provided are `research`, `campaign`, `paper_single`, `paper_portfolio`, and `audit`.

Profiles may adjust safe operational settings such as symbols, timeframes, strategy lists, output paths, and run limits.

Profiles may not enable live mode, live trading, real orders, private API access, leverage, or shorting. Unsafe overlays are rejected before settings validation.

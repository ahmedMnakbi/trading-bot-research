# Quickstart

Run the safe beginner workflow:

```bash
python -m trading_bot install-check
python scripts/generate_fixture_data.py
python -m trading_bot validate-config --config config/default.yaml
python -m trading_bot run-nonlive-smoke --config config/default.yaml
python -m trading_bot build-release-candidate --config config/default.yaml
python -m trading_bot verify-release-candidate --release-dir data/processed/releases/0.1.0-rc1
python -m trading_bot final-nonlive-check --config config/default.yaml
```

This workflow uses fixture data and remains non-live.

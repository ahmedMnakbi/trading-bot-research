# Install

## Windows Setup

Install Python 3.11 or newer from python.org. On Windows, disable the Microsoft Store Python alias if `python` opens the Store instead of running Python: Settings > Apps > Advanced app settings > App execution aliases, then turn off the Python aliases.

## Virtual Environment

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Verify Install

```bash
python -m trading_bot install-check
python scripts/check_all.py
```

The non-live workflow does not require API keys.

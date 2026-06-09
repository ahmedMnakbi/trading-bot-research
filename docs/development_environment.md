# Development Environment

Phase 3 adds project-local checks only. It does not implement a MQL5 EA, trading-enabled EA behavior, Python-controlled prop execution, protected account trading, MT5 login, or prop credential handling.

## What Codex Can Configure

Codex may verify or install Python development tools inside the active project Python environment:

- pytest
- ruff
- pre-commit
- semgrep
- pip-audit

Use:

```powershell
python scripts/install_dev_tools.py
python scripts/install_dev_tools.py --install
```

The install command refuses global/current Python installs unless `--allow-current-python` is explicitly passed. It never installs MT5, MetaEditor, account credentials, terminal settings, or trading permissions.

## What The User Must Install Manually

The user remains responsible for:

- MetaTrader 5 terminal installation
- MetaEditor availability
- Upcomers account login
- broker server selection
- enabling or disabling Algo Trading inside MT5
- attaching any future EA to charts
- Strategy Tester runs that require terminal data

No prop credentials should be placed in the repository, committed to files, printed in logs, or passed to these scripts.

## Environment Check

Use:

```powershell
python scripts/check_dev_environment.py
```

The check reports Python version, broken system `python` alias detection, bundled Codex Python detection, required dependencies, optional local tools, non-live safety gates, and whether the native MQL5 EA prop execution path is documented.

Secret-like environment variable values are redacted. A `WARN` or `SKIPPED` result usually means an optional local tool is missing or an external executable is not installed yet. A `FAIL` means a required safety or dependency check failed.

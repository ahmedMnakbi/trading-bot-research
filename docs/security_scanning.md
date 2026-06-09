# Security Scanning

Security scans are local-only. Do not use cloud scanning modes that upload source code, trading logs, prop-firm account information, or strategy logic without explicit approval.

Use:

```powershell
python scripts/run_security_scans.py
python scripts/run_security_scans.py --strict
```

The script always runs the local Python MT5 execution policy scan. It optionally runs:

- gitleaks, if installed
- pip-audit, if installed
- semgrep, if installed and a local semgrep config exists

Missing optional tools are reported as `SKIPPED` and produce an overall `WARN` unless `--strict` is passed. The semgrep check deliberately avoids cloud or auto configuration.

No MT5 login, prop credentials, or live trading permissions are required.

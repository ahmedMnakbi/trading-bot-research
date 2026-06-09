from __future__ import annotations

import os
from pathlib import Path

from trading_bot.audit.models import ScanResult

SECRET_NAME_PATTERNS = [
    "API_KEY",
    "API_SECRET",
    "EXCHANGE_SECRET",
    "BINANCE",
    "KRAKEN",
    "COINBASE",
    "ALPACA",
    "IBKR",
    "PASSWORD",
    "PRIVATE_KEY",
]
REDACTED = "***REDACTED***"


def scan_environment(
    *,
    environ: dict[str, str] | None = None,
    search_root: str | Path | None = None,
) -> ScanResult:
    env = environ or dict(os.environ)
    warnings = [
        f"{name}={REDACTED}"
        for name in env
        if any(pattern in name.upper() for pattern in SECRET_NAME_PATTERNS)
    ]
    failures: list[str] = []
    if search_root is not None:
        secret_values = [
            value for name, value in env.items() if value and any(
                pattern in name.upper() for pattern in SECRET_NAME_PATTERNS
            )
        ]
        for path in Path(search_root).rglob("*"):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(secret in text for secret in secret_values):
                failures.append(f"secret value leaked in {path}")
    status = "FAIL" if failures else ("WARN" if warnings else "PASS")
    return ScanResult(status=status, warnings=warnings, failures=failures)


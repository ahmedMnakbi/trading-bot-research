from __future__ import annotations

import json
from pathlib import Path

from trading_bot.audit.models import ScanResult

ARTIFACT_FAMILIES = {
    "backtests": Path("data/processed/backtests"),
    "validations": Path("data/processed/validations"),
    "paper": Path("data/processed/paper"),
    "reports": Path("data/processed/reports"),
}


def scan_artifacts(root: str | Path = ".") -> ScanResult:
    base = Path(root)
    failures: list[str] = []
    warnings: list[str] = []
    matches: list[dict[str, object]] = []
    files_scanned = 0
    for family, relative in ARTIFACT_FAMILIES.items():
        directory = base / relative
        if not directory.exists():
            warnings.append(f"no {family}")
            continue
        for path in directory.rglob("*.json"):
            files_scanned += 1
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                warnings.append(f"malformed metadata JSON: {path}")
                continue
            for key in ("live_trading", "real_orders_enabled", "uses_private_api"):
                if data.get(key) is True:
                    failures.append(f"{path} claims {key}=true")
                    matches.append({"path": str(path), "key": key})
    return ScanResult(
        status="FAIL" if failures else ("WARN" if warnings else "PASS"),
        files_scanned=files_scanned,
        matches=matches,
        failures=failures,
        warnings=warnings,
    )


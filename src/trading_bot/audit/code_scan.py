from __future__ import annotations

from pathlib import Path

from trading_bot.audit.models import ScanResult

PROHIBITED_PATTERNS = [
    "create_order",
    "market_order",
    "limit_order",
    "fetch_balance",
    "fetch_positions",
    "fetch_my_trades",
    "privateGet",
    "privatePost",
    "privatePut",
    "privateDelete",
    "apiKey",
    "secret",
    "password",
    "withdraw",
    "transfer",
    "margin",
    "leverage",
    "set_leverage",
    "order" + "_send",
    "order" + "_check",
    "account" + "_info",
    "positions" + "_get",
    "trading_bot.mt5.demo_execution",
    "from trading_bot.mt5 import demo_execution",
]

ALLOWLIST_WORDS = {
    "reject",
    "rejected",
    "prohibit",
    "prohibited",
    "forbidden",
    "disabled",
    "redact",
    "redacted",
    "allowlist",
    "false",
}


def scan_code(root: str | Path = "src/trading_bot") -> ScanResult:
    root_path = Path(root)
    matches: list[dict[str, object]] = []
    allowlisted: list[dict[str, object]] = []
    files_scanned = 0
    for path in root_path.rglob("*.py"):
        files_scanned += 1
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            matches.append(
                {"path": str(path), "line": 0, "pattern": "UNREADABLE", "error": str(exc)}
            )
            continue
        for line_number, line in enumerate(lines, start=1):
            for pattern in PROHIBITED_PATTERNS:
                if pattern.lower() in line.lower():
                    record = {"path": str(path), "line": line_number, "pattern": pattern}
                    if _is_allowlisted(line, path, pattern):
                        allowlisted.append(record)
                    else:
                        matches.append(record)
    failures = [f"{match['path']}:{match['line']} {match['pattern']}" for match in matches]
    return ScanResult(
        status="FAIL" if failures else "PASS",
        files_scanned=files_scanned,
        matches=matches,
        allowlisted_matches=allowlisted,
        failures=failures,
        warnings=[],
    )


def _is_allowlisted(line: str, path: Path, pattern: str) -> bool:
    lowered = line.lower()
    if "test_" in path.name or "audit" in path.parts:
        return True
    if path.as_posix().endswith("src/trading_bot/mt5/demo_execution.py") and pattern in {
        "order" + "_send",
        "order" + "_check",
        "account" + "_info",
    }:
        return "legacy_non_prop_compatible_quarantine" in path.read_text(
            encoding="utf-8",
            errors="ignore",
        ).lower()
    if path.as_posix().endswith("src/trading_bot/mt5/safety.py") and pattern in {
        "trading_bot.mt5.demo_execution",
        "from trading_bot.mt5 import demo_execution",
        "order" + "_send",
        "order" + "_check",
        "account" + "_info",
        "positions" + "_get",
    }:
        return True
    if pattern in {
        "trading_bot.mt5.demo_execution",
        "from trading_bot.mt5 import demo_execution",
    }:
        return False
    if pattern in {"leverage", "margin"} and "allow_leverage" in lowered:
        return True
    if pattern == "leverage" and ("leverage:" in lowered or "leverage !=" in lowered):
        return True
    if pattern in {"apiKey", "secret", "password"} and "redact" in lowered:
        return True
    if pattern in {"apiKey", "secret", "password"} and path.name in {
        "ccxt_provider.py",
        "settings.py",
        "logging.py",
    }:
        return True
    return any(word in lowered for word in ALLOWLIST_WORDS)

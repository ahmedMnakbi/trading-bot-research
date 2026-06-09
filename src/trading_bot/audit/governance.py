from __future__ import annotations

from trading_bot.audit.models import ScanResult
from trading_bot.config.settings import GovernanceSettings


def scan_governance(governance: GovernanceSettings) -> ScanResult:
    failures: list[str] = []
    if not governance.require_human_approval_for_live:
        failures.append("human approval must remain mandatory")
    if governance.live_trading_allowed:
        failures.append("live_trading_allowed must remain false")
    if governance.real_orders_allowed:
        failures.append("real_orders_allowed must remain false")
    if governance.private_api_allowed:
        failures.append("private_api_allowed must remain false")
    return ScanResult(status="FAIL" if failures else "PASS", failures=failures)


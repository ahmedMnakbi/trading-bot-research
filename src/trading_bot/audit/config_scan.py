from __future__ import annotations

from trading_bot.audit.models import ScanResult
from trading_bot.config.settings import Settings


def scan_config(settings: Settings) -> ScanResult:
    failures: list[str] = []
    mode = _get(settings, "mode")
    mode_value = getattr(mode, "value", mode)
    if mode_value == "live":
        failures.append("mode must not be live")
    if _get(settings, "live_trading_enabled"):
        failures.append("live_trading_enabled must be false")
    governance = _get(settings, "governance")
    risk = _get(settings, "risk")
    safety = _get(settings, "safety")
    if _get(governance, "live_trading_allowed"):
        failures.append("governance.live_trading_allowed must be false")
    if _get(governance, "real_orders_allowed"):
        failures.append("governance.real_orders_allowed must be false")
    if _get(governance, "private_api_allowed"):
        failures.append("governance.private_api_allowed must be false")
    if not _get(governance, "require_human_approval_for_live"):
        failures.append("human approval must be required for live")
    if _get(risk, "allow_leverage"):
        failures.append("leverage must be disabled")
    if _get(risk, "allow_shorting"):
        failures.append("shorting must be disabled")
    if not _get(risk, "require_stop_loss"):
        failures.append("stop-loss must be required")
    if not _get(safety, "kill_switch_armed"):
        failures.append("kill switch must be armed")
    if _get(risk, "risk_per_trade_pct", 0) > 2:
        failures.append("risk per trade must be at or below 2%")
    return ScanResult(status="FAIL" if failures else "PASS", failures=failures)


def _get(obj: object, key: str, default: object = None) -> object:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

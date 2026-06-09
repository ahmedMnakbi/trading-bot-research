from __future__ import annotations

from trading_bot.audit.governance import scan_governance
from trading_bot.config.settings import GovernanceSettings


def test_governance_passes_safe_defaults() -> None:
    assert scan_governance(GovernanceSettings()).status == "PASS"


def test_governance_fails_when_live_trading_allowed() -> None:
    assert scan_governance(GovernanceSettings(live_trading_allowed=True)).status == "FAIL"


def test_governance_fails_when_real_orders_allowed() -> None:
    assert scan_governance(GovernanceSettings(real_orders_allowed=True)).status == "FAIL"


def test_governance_fails_when_private_api_allowed() -> None:
    assert scan_governance(GovernanceSettings(private_api_allowed=True)).status == "FAIL"


from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from trading_bot.audit.config_scan import scan_config
from trading_bot.audit.governance import scan_governance
from trading_bot.config.settings import Settings


def settings_with(**changes):  # type: ignore[no-untyped-def]
    data = yaml.safe_load(Path("config/default.yaml").read_text(encoding="utf-8"))
    for path, value in changes.items():
        target = data
        parts = path.split("__")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    return Settings.model_validate(data)


def test_audit_fails_when_config_has_mode_live(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_LIVE_TRADING", "true")
    settings = settings_with(mode="live", live_trading_enabled=True)

    assert scan_config(settings).status == "FAIL"


def test_audit_fails_when_live_trading_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_LIVE_TRADING", "true")
    settings = settings_with(live_trading_enabled=True, mode="live")

    assert scan_config(settings).status == "FAIL"


def test_audit_fails_when_leverage_is_enabled() -> None:
    data = yaml.safe_load(Path("config/default.yaml").read_text(encoding="utf-8"))
    data["risk"]["allow_leverage"] = True
    settings = Settings.model_construct(**data)

    assert scan_config(settings).status == "FAIL"


def test_audit_fails_when_shorting_is_enabled() -> None:
    data = yaml.safe_load(Path("config/default.yaml").read_text(encoding="utf-8"))
    data["risk"]["allow_shorting"] = True
    settings = Settings.model_construct(**data)

    assert scan_config(settings).status == "FAIL"


def test_audit_fails_when_stop_loss_is_not_required() -> None:
    data = yaml.safe_load(Path("config/default.yaml").read_text(encoding="utf-8"))
    data["risk"]["require_stop_loss"] = False
    settings = Settings.model_construct(**data)

    assert scan_config(settings).status == "FAIL"


def test_audit_fails_when_kill_switch_is_not_armed() -> None:
    data = yaml.safe_load(Path("config/default.yaml").read_text(encoding="utf-8"))
    data["safety"]["kill_switch_armed"] = False
    settings = Settings.model_construct(**data)

    assert scan_config(settings).status == "FAIL"


def test_governance_fails_when_live_orders_or_private_are_allowed() -> None:
    settings = settings_with(governance__live_trading_allowed=True)
    assert scan_governance(settings.governance).status == "FAIL"
    settings = settings_with(governance__real_orders_allowed=True)
    assert scan_governance(settings.governance).status == "FAIL"
    settings = settings_with(governance__private_api_allowed=True)
    assert scan_governance(settings.governance).status == "FAIL"


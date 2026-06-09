from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from trading_bot.config.settings import load_settings


def write_config(tmp_path: Path, data: dict[str, object]) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


@pytest.fixture()
def default_config_data() -> dict[str, object]:
    return yaml.safe_load(Path("config/default.yaml").read_text(encoding="utf-8"))


def test_default_config_validates() -> None:
    settings = load_settings("config/default.yaml")

    assert settings.mode == "paper"
    assert settings.live_trading_enabled is False
    assert settings.safety.kill_switch_armed is True


def test_config_fails_when_risk_per_trade_above_two_percent(
    tmp_path: Path, default_config_data: dict[str, object]
) -> None:
    risk = dict(default_config_data["risk"])  # type: ignore[index]
    risk["risk_per_trade_pct"] = 2.01
    default_config_data["risk"] = risk

    with pytest.raises(ValidationError):
        load_settings(write_config(tmp_path, default_config_data))


def test_config_fails_when_leverage_enabled(
    tmp_path: Path, default_config_data: dict[str, object]
) -> None:
    risk = dict(default_config_data["risk"])  # type: ignore[index]
    risk["allow_leverage"] = True
    default_config_data["risk"] = risk

    with pytest.raises(ValidationError):
        load_settings(write_config(tmp_path, default_config_data))


def test_config_fails_when_live_mode_lacks_environment_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, default_config_data: dict[str, object]
) -> None:
    monkeypatch.delenv("ALLOW_LIVE_TRADING", raising=False)
    default_config_data["mode"] = "live"
    default_config_data["live_trading_enabled"] = True

    with pytest.raises(ValidationError):
        load_settings(write_config(tmp_path, default_config_data))


def test_config_fails_when_stop_loss_not_required(
    tmp_path: Path, default_config_data: dict[str, object]
) -> None:
    risk = dict(default_config_data["risk"])  # type: ignore[index]
    risk["require_stop_loss"] = False
    default_config_data["risk"] = risk

    with pytest.raises(ValidationError):
        load_settings(write_config(tmp_path, default_config_data))


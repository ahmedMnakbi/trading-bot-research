from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from trading_bot.main import app
from trading_bot.mt5.models import load_mt5_readonly_config


def test_mt5_readonly_config_defaults_are_safe() -> None:
    config = load_mt5_readonly_config(Path("config/mt5_readonly.yaml"))

    assert config.mode == "paper"
    assert config.live_trading_enabled is False
    assert config.execution_enabled is False
    assert config.real_orders_allowed is False
    assert config.private_api_allowed is False
    assert config.allow_leverage is False
    assert config.allow_shorting is False
    assert config.discovery.enabled is True
    assert config.session.timezone == "America/New_York"


@pytest.mark.parametrize(
    "unsafe_payload",
    [
        {"mode": "live"},
        {"live_trading_enabled": True},
        {"execution_enabled": True},
        {"real_orders_allowed": True},
        {"private_api_allowed": True},
        {"allow_leverage": True},
        {"allow_shorting": True},
    ],
)
def test_mt5_readonly_config_rejects_unsafe_flags(
    tmp_path: Path, unsafe_payload: dict[str, object]
) -> None:
    path = tmp_path / "mt5_readonly.yaml"
    path.write_text(yaml.safe_dump(unsafe_payload), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_mt5_readonly_config(path)


def test_mt5_readonly_cli_can_validate_without_terminal_init(tmp_path: Path) -> None:
    path = tmp_path / "mt5_readonly.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "mode": "paper",
                "live_trading_enabled": False,
                "execution_enabled": False,
                "real_orders_allowed": False,
                "private_api_allowed": False,
                "allow_leverage": False,
                "allow_shorting": False,
                "terminal": {"initialize": False},
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["mt5-readonly-check", "--config", str(path)])

    assert result.exit_code == 0
    assert "MT5 read-only configuration valid" in result.output
    assert "live_trading: false" in result.output
    assert "real_orders_enabled: false" in result.output
    assert "uses_private_api: false" in result.output
    assert "terminal_connection_available: skipped" in result.output

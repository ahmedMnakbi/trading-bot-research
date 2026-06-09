from __future__ import annotations

import json
from pathlib import Path

import pytest

from trading_bot.config.settings import load_settings
from trading_bot.utils.logging import configure_logging, get_logger


def test_default_mode_is_not_live() -> None:
    settings = load_settings("config/default.yaml")

    assert settings.mode.value in {"paper", "backtest"}
    assert settings.mode.value != "live"


def test_default_config_has_no_live_trading_enabled() -> None:
    raw = Path("config/default.yaml").read_text(encoding="utf-8")

    assert "live_trading_enabled: false" in raw


def test_logging_redacts_secrets(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(mode="paper", component="test")
    logger = get_logger(component="logging-test", mode="paper")

    logger.info("secret_check", api_secret="super-secret", nested={"api_key": "key-123"})

    output = capsys.readouterr().out.strip()
    payload = json.loads(output)

    assert payload["timestamp"]
    assert payload["mode"] == "paper"
    assert payload["component"] == "logging-test"
    assert payload["level"] == "info"
    assert payload["api_secret"] == "[REDACTED]"
    assert payload["nested"]["api_key"] == "[REDACTED]"
    assert "super-secret" not in output
    assert "key-123" not in output


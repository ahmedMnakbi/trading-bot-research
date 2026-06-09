from __future__ import annotations

from typer.testing import CliRunner

from trading_bot.main import app
from trading_bot.version import __version__


def test_version_command_outputs_non_live_metadata() -> None:
    result = CliRunner().invoke(app, ["version"])

    assert result.exit_code == 0
    assert f"trading-bot {__version__}" in result.output
    assert "live_trading: false" in result.output
    assert "real_orders_enabled: false" in result.output
    assert "uses_private_api: false" in result.output

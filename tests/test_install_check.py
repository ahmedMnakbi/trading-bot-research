from __future__ import annotations

from typer.testing import CliRunner

from trading_bot.main import app
from trading_bot.release.final_check import run_install_check


def test_install_check_help_works() -> None:
    assert CliRunner().invoke(app, ["install-check", "--help"]).exit_code == 0


def test_install_check_reports_non_live_safety_metadata() -> None:
    result = CliRunner().invoke(app, ["install-check"])

    assert result.exit_code == 0, result.output
    assert "live_trading: false" in result.output
    assert "real_orders_enabled: false" in result.output
    assert "uses_private_api: false" in result.output


def test_install_check_function_passes() -> None:
    assert run_install_check()["status"] == "PASS"

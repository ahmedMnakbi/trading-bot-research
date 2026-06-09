from __future__ import annotations

from trading_bot.audit.env_scan import REDACTED, scan_environment


def test_env_scan_redacts_secret_like_values() -> None:
    result = scan_environment(environ={"API_KEY": "super-secret"})

    assert REDACTED in result.warnings[0]
    assert "super-secret" not in str(result.warnings)


def test_env_scan_warns_when_secret_like_variable_names_exist() -> None:
    assert scan_environment(environ={"KRAKEN_API_KEY": "x"}).status == "WARN"


from __future__ import annotations

from pathlib import Path

import pytest

from scripts import check_dev_environment, install_dev_tools

ROOT = Path(__file__).resolve().parents[1]


def test_check_dev_environment_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        check_dev_environment.main(["--help"])

    assert excinfo.value.code == 0
    assert "development environment" in capsys.readouterr().out.lower()


def test_install_dev_tools_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        install_dev_tools.main(["--help"])

    assert excinfo.value.code == 0
    assert "project-local Python development tools" in capsys.readouterr().out


def test_secret_like_environment_keys_are_redacted() -> None:
    redacted = check_dev_environment.redact_environment(
        {
            "UPCOMERS_PASSWORD": "do-not-print",
            "ACCOUNT_TOKEN": "do-not-print",
            "NORMAL_VALUE": "visible",
        }
    )

    assert redacted["UPCOMERS_PASSWORD"] == "<redacted>"
    assert redacted["ACCOUNT_TOKEN"] == "<redacted>"
    assert redacted["NORMAL_VALUE"] == "visible"


def test_dev_environment_checks_do_not_require_mt5_credentials() -> None:
    results = check_dev_environment.run_checks(
        root=ROOT,
        env={"UPCOMERS_PASSWORD": "secret", "NORMAL_VALUE": "visible"},
    )

    assert any(result.name == "environment_redaction" for result in results)
    assert any(result.name == "native_mql5_ea_documented" for result in results)
    assert all("prop credential" not in result.message.lower() for result in results)

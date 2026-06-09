from __future__ import annotations

from pathlib import Path

import pytest

from scripts import check_all


class Result:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode


def test_check_all_runs_commands_in_expected_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(command: tuple[str, ...], check: bool, **_: object) -> Result:
        calls.append(command)
        return Result(0)

    monkeypatch.setattr(check_all, "ensure_repo_root", lambda: Path.cwd())
    monkeypatch.setattr(check_all.subprocess, "run", fake_run)

    assert check_all.run_steps(check_all.default_steps()) == 0

    assert [command[1:] for command in calls] == [
        ("scripts/check_dev_environment.py",),
        ("scripts/check_metaeditor.py",),
        ("scripts/run_mql5_source_scan.py",),
        ("scripts/compile_mql5_ea.py",),
        ("scripts/run_security_scans.py",),
        ("-m", "ruff", "check", "."),
        ("-m", "pytest"),
        ("-m", "trading_bot", "validate-config", "--config", "config/default.yaml"),
        ("-m", "trading_bot", "run-safety-audit", "--config", "config/default.yaml"),
    ]


def test_check_all_fails_cleanly_when_command_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(command: tuple[str, ...], check: bool, **_: object) -> Result:
        calls.append(command)
        return Result(7 if len(calls) == 2 else 0)

    monkeypatch.setattr(check_all, "ensure_repo_root", lambda: Path.cwd())
    monkeypatch.setattr(check_all.subprocess, "run", fake_run)

    assert check_all.run_steps(check_all.default_steps()) == 7
    assert len(calls) == 2


def test_check_all_redacts_secret_like_environment_values() -> None:
    redacted = check_all.redacted_environment(
        {
            "EXCHANGE_API_KEY": "abc",
            "NORMAL_SETTING": "visible",
            "PASSWORD": "secret",
        }
    )

    assert redacted["EXCHANGE_API_KEY"] == "<redacted>"
    assert redacted["PASSWORD"] == "<redacted>"
    assert redacted["NORMAL_SETTING"] == "visible"

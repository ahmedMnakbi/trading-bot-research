from __future__ import annotations

from pathlib import Path

import pytest

from scripts import check_safety


class Result:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode


def test_check_safety_runs_config_validation_before_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(command: tuple[str, ...], check: bool) -> Result:
        calls.append(command)
        return Result(0)

    monkeypatch.setattr(check_safety, "ensure_repo_root", lambda: Path.cwd())
    monkeypatch.setattr(check_safety.subprocess, "run", fake_run)

    assert check_safety.run_steps(check_safety.safety_steps()) == 0

    assert calls[0][1:] == (
        "-m",
        "trading_bot",
        "validate-config",
        "--config",
        "config/default.yaml",
    )
    assert calls[1][1:] == (
        "-m",
        "trading_bot",
        "run-safety-audit",
        "--config",
        "config/default.yaml",
    )


def test_check_safety_exits_nonzero_on_safety_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    codes = iter([0, 9])

    def fake_run(command: tuple[str, ...], check: bool) -> Result:
        return Result(next(codes))

    monkeypatch.setattr(check_safety, "ensure_repo_root", lambda: Path.cwd())
    monkeypatch.setattr(check_safety.subprocess, "run", fake_run)

    assert check_safety.run_steps(check_safety.safety_steps()) == 9

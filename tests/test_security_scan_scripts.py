from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_security_scans


def test_run_security_scans_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        run_security_scans.main(["--help"])

    assert excinfo.value.code == 0
    assert "local-only" in capsys.readouterr().out


def test_missing_optional_security_tools_are_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_security_scans.shutil, "which", lambda _: None)
    (tmp_path / "src" / "trading_bot").mkdir(parents=True)

    results = run_security_scans.run_security_scans(tmp_path)

    assert run_security_scans.overall_status(results) == "WARN"
    assert {result.name for result in results if result.status == "SKIPPED"} == {
        "gitleaks",
        "pip-audit",
        "semgrep",
    }


def test_strict_security_scan_fails_when_optional_tools_are_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_security_scans.shutil, "which", lambda _: None)
    (tmp_path / "src" / "trading_bot").mkdir(parents=True)

    results = run_security_scans.run_security_scans(tmp_path, strict=True)

    assert run_security_scans.overall_status(results) == "FAIL"


def test_semgrep_scan_uses_local_config_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], check: bool) -> object:
        commands.append(command)

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr(run_security_scans.shutil, "which", lambda command: command)
    monkeypatch.setattr(run_security_scans.subprocess, "run", fake_run)
    (tmp_path / "src" / "trading_bot").mkdir(parents=True)
    (tmp_path / "semgrep.yml").write_text("rules: []\n", encoding="utf-8")

    results = run_security_scans.run_security_scans(tmp_path)

    assert run_security_scans.overall_status(results) == "PASS"
    semgrep_command = [command for command in commands if command[0] == "semgrep"][0]
    assert "--config" in semgrep_command
    assert "auto" not in semgrep_command
    assert "--metrics=off" in semgrep_command

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import check_metaeditor


def test_check_metaeditor_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        check_metaeditor.main(["--help"])

    assert excinfo.value.code == 0
    assert "MetaEditor" in capsys.readouterr().out


def test_missing_metaeditor_gives_graceful_skipped_result(tmp_path: Path) -> None:
    detection = check_metaeditor.detect_metaeditor(
        metaeditor_path=tmp_path / "missing-metaeditor64.exe",
        terminal_path=tmp_path / "missing-terminal64.exe",
    )

    assert detection.status == "SKIPPED"
    assert detection.metaeditor_path is None
    assert "install MetaTrader 5 manually" in detection.message


def test_fake_metaeditor_and_terminal_are_detected(tmp_path: Path) -> None:
    metaeditor = tmp_path / "metaeditor64.exe"
    terminal = tmp_path / "terminal64.exe"
    metaeditor.write_text("", encoding="utf-8")
    terminal.write_text("", encoding="utf-8")

    detection = check_metaeditor.detect_metaeditor(metaeditor, terminal)

    assert detection.status == "PASS"
    assert detection.metaeditor_path == str(metaeditor)
    assert detection.terminal_path == str(terminal)

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import compile_mql5_ea, run_mql5_source_scan


def test_run_mql5_source_scan_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        run_mql5_source_scan.main(["--help"])

    assert excinfo.value.code == 0
    assert "MQL5 source tree" in capsys.readouterr().out


def test_compile_mql5_ea_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        compile_mql5_ea.main(["--help"])

    assert excinfo.value.code == 0
    assert "MQL5 EA" in capsys.readouterr().out


def test_no_mql5_tree_gives_skipped_source_scan(tmp_path: Path) -> None:
    result = run_mql5_source_scan.run_mql5_source_scan(tmp_path)

    assert result.status == "SKIPPED"


def test_no_ea_source_gives_skipped_compile_and_writes_log(tmp_path: Path) -> None:
    result = compile_mql5_ea.compile_ea(tmp_path)

    assert result.status == "SKIPPED"
    assert Path(result.log_path).exists()
    assert "EA source does not exist yet" in Path(result.log_path).read_text(encoding="utf-8")


def test_fake_ea_source_with_banned_term_fails_source_scan(tmp_path: Path) -> None:
    source = tmp_path / "mql5" / "Experts" / "Unsafe" / "Unsafe.mq5"
    source.parent.mkdir(parents=True)
    source.write_text("void OnTick() { string mode = \"martingale grid\"; }\n", encoding="utf-8")

    result = run_mql5_source_scan.run_mql5_source_scan(tmp_path)

    patterns = {violation["pattern"] for violation in result.violations}
    assert result.status == "FAIL"
    assert "martingale" in patterns
    assert "grid_trading" in patterns


def test_fake_ea_source_missing_required_guards_fails_after_source_exists(tmp_path: Path) -> None:
    source = tmp_path / "mql5" / "Experts" / "Unsafe" / "Unsafe.mq5"
    source.parent.mkdir(parents=True)
    source.write_text("input bool EnableTrading=false;\nvoid OnTick() {}\n", encoding="utf-8")

    result = run_mql5_source_scan.run_mql5_source_scan(tmp_path)

    patterns = {violation["pattern"] for violation in result.violations}
    assert result.status == "FAIL"
    assert "manual_confirmation_guard" in patterns
    assert "phase5_config_validation" in patterns
    assert "approval_metadata_guard" in patterns
    assert "minimum_hold_guard" in patterns
    assert "daily_loss_guard" in patterns


def test_fake_ea_source_with_order_call_fails_source_scan(tmp_path: Path) -> None:
    source = tmp_path / "mql5" / "Experts" / "Unsafe" / "Unsafe.mq5"
    source.parent.mkdir(parents=True)
    source.write_text(
        "input bool EnableTrading=false;\nvoid OnTick() { OrderSend(request, result); }\n",
        encoding="utf-8",
    )

    result = run_mql5_source_scan.run_mql5_source_scan(tmp_path)

    patterns = {violation["pattern"] for violation in result.violations}
    assert result.status == "FAIL"
    assert "mql5_order_send" in patterns

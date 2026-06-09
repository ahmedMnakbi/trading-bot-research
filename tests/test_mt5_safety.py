from __future__ import annotations

from pathlib import Path

import pytest

from trading_bot.mt5.safety import (
    assert_mt5_read_only_source,
    find_mql5_source_scan_violations,
    find_mt5_prohibited_patterns,
)


def test_mt5_safety_scanner_blocks_execution_patterns(tmp_path: Path) -> None:
    source = tmp_path / "src" / "trading_bot" / "mt5" / "execution.py"
    source.parent.mkdir(parents=True)
    source.write_text("def bad(client):\n    return client.order_send({})\n", encoding="utf-8")

    matches = find_mt5_prohibited_patterns(tmp_path)

    assert len(matches) == 1
    assert matches[0]["pattern"] == "order_send"
    with pytest.raises(ValueError, match="prohibited"):
        assert_mt5_read_only_source(tmp_path)


def test_mt5_safety_scanner_allows_explicit_docs_and_tests(tmp_path: Path) -> None:
    docs_file = tmp_path / "docs" / "mt5_safety_model.md"
    tests_file = tmp_path / "tests" / "test_mt5_safety.py"
    docs_file.parent.mkdir()
    tests_file.parent.mkdir()
    docs_file.write_text("The scanner must mention order_check in docs.\n", encoding="utf-8")
    tests_file.write_text("def test_blocked():\n    assert 'positions_get'\n", encoding="utf-8")

    assert find_mt5_prohibited_patterns(tmp_path) == []


def test_current_mt5_source_is_read_only() -> None:
    assert_mt5_read_only_source(Path("src") / "trading_bot")


def test_mt5_safety_scanner_blocks_python_execution_imports(tmp_path: Path) -> None:
    source = tmp_path / "src" / "trading_bot" / "mt5" / "prop_workflow.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "from trading_bot.mt5.demo_execution import Mt5DemoExecutionClient\n",
        encoding="utf-8",
    )

    matches = find_mt5_prohibited_patterns(tmp_path)

    assert len(matches) == 1
    assert Path(str(matches[0]["path"])).parts[-3:] == ("trading_bot", "mt5", "prop_workflow.py")
    assert matches[0]["line"] == 1
    assert matches[0]["pattern"] == "python_mt5_execution_import"


def test_mql5_source_scan_detects_missing_required_controls(tmp_path: Path) -> None:
    ea = tmp_path / "mql5" / "Experts" / "Unsafe" / "Unsafe.mq5"
    ea.parent.mkdir(parents=True)
    ea.write_text("void OnTick() { /* no controls */ }\n", encoding="utf-8")

    patterns = {match["pattern"] for match in find_mql5_source_scan_violations(tmp_path)}

    assert "manual_confirmation_guard" in patterns
    assert "trading_disabled_default" in patterns
    assert "minimum_hold_guard" in patterns
    assert "server_message_counter" in patterns
    assert "daily_loss_guard" in patterns
    assert "overall_loss_guard" in patterns


def test_mql5_source_scan_flags_banned_strategy_terms(tmp_path: Path) -> None:
    ea = tmp_path / "mql5" / "Experts" / "Unsafe" / "Unsafe.mq5"
    ea.parent.mkdir(parents=True)
    ea.write_text("void OnTick() { string mode = \"martingale grid\"; }\n", encoding="utf-8")

    patterns = {match["pattern"] for match in find_mql5_source_scan_violations(tmp_path)}

    assert "martingale" in patterns
    assert "grid_trading" in patterns

from __future__ import annotations

from trading_bot.audit.code_scan import scan_code


def test_code_scan_fails_on_unallowlisted_create_order(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "x.py"
    path.write_text("client.create_order()\n", encoding="utf-8")

    assert scan_code(tmp_path).status == "FAIL"


def test_code_scan_fails_on_unallowlisted_fetch_balance(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "x.py"
    path.write_text("client.fetch_balance()\n", encoding="utf-8")

    assert scan_code(tmp_path).status == "FAIL"


def test_code_scan_does_not_fail_on_explicit_rejection_guard_text(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "x.py"
    path.write_text("raise ValueError('create_order is forbidden')\n", encoding="utf-8")

    assert scan_code(tmp_path).status == "PASS"


def test_code_scan_fails_on_python_mt5_execution_import(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "prop_workflow.py"
    path.write_text(
        "from trading_bot.mt5.demo_execution import Mt5DemoExecutionClient\n",
        encoding="utf-8",
    )

    result = scan_code(tmp_path)

    assert result.status == "FAIL"
    assert result.matches[0]["pattern"] == "trading_bot.mt5.demo_execution"

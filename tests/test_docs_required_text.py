from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_install_mentions_windows_python_alias_issue() -> None:
    assert "Microsoft Store Python alias" in (ROOT / "INSTALL.md").read_text(encoding="utf-8")


def test_safety_contains_required_non_live_statement() -> None:
    text = (ROOT / "SAFETY.md").read_text(encoding="utf-8")
    assert (
        "This project is non-live. It does not implement real exchange order placement, "
        "authenticated exchange clients, private account endpoints, leverage, short selling, "
        "optimization, or machine learning. It is not approved for real-money trading."
    ) in text


def test_security_says_no_api_keys_needed() -> None:
    assert "No API keys are needed for non-live mode" in (ROOT / "SECURITY.md").read_text(
        encoding="utf-8"
    )


def test_command_reference_includes_all_groups() -> None:
    text = (ROOT / "docs/command_reference.md").read_text(encoding="utf-8")
    for group in [
        "Config",
        "Data",
        "Backtesting",
        "Validation",
        "Campaigns",
        "Paper Trading",
        "Portfolio Paper Trading",
        "Reporting",
        "Failure Injection",
        "Incident Replay",
        "Audit",
        "Operator Tools",
        "Release Tools",
    ]:
        assert f"## {group}" in text


def test_known_limitations_says_paper_trading_can_mislead() -> None:
    assert "Paper trading can mislead" in (
        ROOT / "docs/known_limitations.md"
    ).read_text(encoding="utf-8")


def test_agents_instructions_lock_native_mql5_execution_path() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "Native MQL5 Expert Advisor code is the only prop-firm execution path" in text
    assert "Python-controlled MT5 execution is not allowed" in text
    assert "Trading must stay disabled by default" in text

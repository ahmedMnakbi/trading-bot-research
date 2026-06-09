from __future__ import annotations

from pathlib import Path

DOCS = {
    name: Path("docs") / name
    for name in [
        "mt5_ea_installation.md",
        "trial_monitor_only_runbook.md",
        "broker_time_verification.md",
        "symbol_session_verification.md",
        "trial_observation_evidence.md",
    ]
}


def _read(name: str) -> str:
    return DOCS[name].read_text(encoding="utf-8")


def test_phase10_docs_exist() -> None:
    for path in DOCS.values():
        assert path.exists()


def test_installation_and_runbook_require_trial_only_first() -> None:
    combined = _read("mt5_ea_installation.md") + _read("trial_monitor_only_runbook.md")

    assert "Trial Risk-Free account first" in combined
    assert "Trial Risk-Free account only" in combined
    assert "Do not attach the EA to Surge 2 Step or Vanguard" in combined
    assert "Do not attach to Surge 2 Step or Vanguard" in combined


def test_docs_block_surge_vanguard_and_trading_approval() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in DOCS.values())

    for required in [
        "Surge 2 Step",
        "Vanguard",
        "blocked",
        "not approval",
        "Trial success is not prop challenge approval",
        "Strategy Tester evidence",
        "trial_monitor_smoke",
        "formal_trial_observation",
        "Raw MT5 Experts/Journal logs are required for formal audit",
        "Screenshots are optional",
        "raw MT5 logs",
        "no_order_no_position_note.txt",
        "Final Audit Agent review",
        "Exact Surge 2 Step rules",
        "Vanguard rules remain unresolved",
    ]:
        assert required in combined


def test_docs_require_enable_trading_false_and_monitor_only() -> None:
    combined = _read("mt5_ea_installation.md") + _read("trial_monitor_only_runbook.md")

    assert "EnableTrading=false" in combined
    assert "EnablePropChallengeMode=false" in combined
    assert "AccountProgram=TrialRiskFree" in combined
    assert "monitor-only" in combined.lower()


def test_docs_include_broker_time_symbol_session_and_emergency_stop() -> None:
    runbook = _read("trial_monitor_only_runbook.md")
    broker_time = _read("broker_time_verification.md")
    symbol_session = _read("symbol_session_verification.md")

    assert "BrokerServerUtcOffsetMinutes" in broker_time
    assert "compare MT5 Market Watch/server time to UTC".lower() in broker_time.lower()
    assert "DST" in broker_time
    assert "forex symbols" in symbol_session
    assert "XAUUSD" in symbol_session
    assert "NAS" in symbol_session
    assert "BTC" in symbol_session
    assert "Emergency Stop" in runbook
    assert "remove the EA from the chart".lower() in runbook.lower()
    assert "disable Algo Trading".lower() in runbook.lower()


def test_docs_never_request_credentials() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in DOCS.values())

    assert (
        "Do not provide passwords" in combined
        or "Never include or request account passwords" in combined
    )
    assert "--password" not in combined
    assert "--credentials" not in combined

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EA_SOURCE = (
    ROOT
    / "mql5"
    / "Experts"
    / "UpcomersNYSessionPropBot"
    / "UpcomersNYSessionPropBot.mq5"
)
INCLUDE_ROOT = ROOT / "mql5" / "Include" / "UpcomersNYSessionPropBot"
TRIAL_EXECUTION = INCLUDE_ROOT / "TrialExecution.mqh"
TESTER_EXECUTION = INCLUDE_ROOT / "TesterExecution.mqh"


def _call_block(text: str, call_name: str) -> str:
    match = re.search(
        rf"{re.escape(call_name)}\(\n(?P<body>.*?)\n\s*\);",
        text,
        re.DOTALL,
    )
    assert match, f"missing call {call_name}"
    return match.group("body")


def _argument_count(call_body: str) -> int:
    return len([line for line in call_body.splitlines() if line.strip()])


def test_trial_execution_call_matches_eight_argument_signature() -> None:
    ea_text = EA_SOURCE.read_text(encoding="utf-8")
    trial_text = TRIAL_EXECUTION.read_text(encoding="utf-8")
    call_body = _call_block(ea_text, "g_trialExecution.ProcessDecision")

    assert _argument_count(call_body) == 8
    assert "IsStrategyTesterRuntime()" not in call_body
    assert "CMessageCounter &messageCounter" in trial_text
    assert "const bool isStrategyTesterRuntime" not in trial_text


def test_tester_execution_call_matches_nine_argument_signature() -> None:
    ea_text = EA_SOURCE.read_text(encoding="utf-8")
    tester_text = TESTER_EXECUTION.read_text(encoding="utf-8")
    call_body = _call_block(ea_text, "g_testerExecution.ProcessDecision")

    assert _argument_count(call_body) == 9
    assert "IsStrategyTesterRuntime()" in call_body
    assert "const bool isStrategyTesterRuntime" in tester_text
    assert "ValidateStrategyTesterExecutionConfig(config, isStrategyTesterRuntime" in (
        tester_text
    )


def test_order_calls_remain_in_only_two_isolated_modules() -> None:
    allowed = {TRIAL_EXECUTION, TESTER_EXECUTION}
    assert TRIAL_EXECUTION.read_text(encoding="utf-8").count("OrderSend(request, result)") == 1
    assert TESTER_EXECUTION.read_text(encoding="utf-8").count("OrderSend(request, result)") == 1

    for path in (ROOT / "mql5").rglob("*"):
        if path.suffix.lower() not in {".mq5", ".mqh"} or path in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in [
            "OrderSend",
            "CTrade",
            ".Buy(",
            ".Sell(",
            "PositionOpen",
            "BuyLimit",
            "SellLimit",
            "BuyStop",
            "SellStop",
        ]:
            assert pattern not in text

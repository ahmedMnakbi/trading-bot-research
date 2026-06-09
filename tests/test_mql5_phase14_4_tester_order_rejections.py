from __future__ import annotations

from pathlib import Path

from scripts.parse_strategy_tester_report import parse_strategy_tester_report

ROOT = Path(__file__).resolve().parents[1]
MQL5_ROOT = ROOT / "mql5"
INCLUDE_ROOT = MQL5_ROOT / "Include" / "UpcomersNYSessionPropBot"
TESTER_EXECUTION = INCLUDE_ROOT / "TesterExecution.mqh"
TRIAL_EXECUTION = INCLUDE_ROOT / "TrialExecution.mqh"


def _tester_text() -> str:
    return TESTER_EXECUTION.read_text(encoding="utf-8")


def test_tester_rejection_logging_includes_request_and_symbol_metadata() -> None:
    text = _tester_text()

    for token in [
        "TESTER_EXECUTION_BROKER_RESPONSE",
        "TESTER_EXECUTION_ORDER_REJECTED",
        "retcode=%u",
        "comment=%s",
        "request.action=%s",
        "request.type=%s",
        "request.symbol=%s",
        "request.volume=%.8f",
        "request.price=%.8f",
        "request.sl=%.8f",
        "request.tp=%.8f",
        "request.deviation=%d",
        "request.type_filling=%s",
        "SYMBOL_FILLING_MODE=%d",
        "SYMBOL_TRADE_MODE=%d",
        "SYMBOL_TRADE_STOPS_LEVEL=%d",
        "SYMBOL_TRADE_FREEZE_LEVEL=%d",
        "SYMBOL_VOLUME_MIN=%.8f",
        "SYMBOL_VOLUME_STEP=%.8f",
        "bid=%.8f",
        "ask=%.8f",
        "point=%.10f",
        "digits=%d",
    ]:
        assert token in text


def test_tester_filling_mode_is_derived_from_symbol_metadata() -> None:
    text = _tester_text()

    assert "ResolveTesterFillingMode" in text
    assert "SYMBOL_FILLING_MODE" in text
    assert "SYMBOL_FILLING_IOC" in text
    assert "ORDER_FILLING_IOC" in text
    assert "SYMBOL_FILLING_FOK" in text
    assert "ORDER_FILLING_FOK" in text
    assert "ORDER_FILLING_RETURN" in text
    assert "request.type_filling = fillingMode" in text
    assert "TESTER_FILLING_MODE" in text


def test_tester_request_normalizes_price_sltp_and_volume() -> None:
    text = _tester_text()

    assert "NormalizeDouble(entryPriceRaw" in text
    assert "NormalizeDouble(decision.SuggestedStopLoss" in text
    assert "NormalizeDouble(decision.SuggestedTakeProfit" in text
    assert "TESTER_ORDER_NORMALIZED" in text
    assert "NormalizeVolumeToMinStep" in text
    assert "VOLUME_NORMALIZED_TO_MIN_STEP" in text
    assert "VolumeDigitsFromStep" in text
    assert "ValidateRequestGeometry" in text


def test_parser_summarizes_tester_rejection_retcodes_and_comments(tmp_path: Path) -> None:
    report = tmp_path / "tester_rejections.log"
    report.write_text(
        "\n".join(
            [
                "StrategyTesterExecutionMode=true",
                "EnableTrading=false",
                "EnableTrialExecution=false",
                "EnablePropChallengeMode=false",
                "Total trades: 0",
                "Orders: 0",
                "Deals: 0",
                (
                    "STRATEGY_DIAGNOSTICS_SUMMARY "
                    "strategy=STRATEGY_VWAP_TREND_CONTINUATION "
                    "total_evaluations=12269 enter_long=21 enter_short=19 "
                    "tester_execution_mode=true tester_runtime=true "
                    "tester_orders_attempted=40 top_reason_codes=ENTER_LONG_INTENT:21"
                ),
                (
                    "TESTER_EXECUTION_BROKER_RESPONSE simulated=true sent=false "
                    "retcode=10030 order=0 deal=0 comment=Unsupported filling mode no_retry=true "
                    "request.action=TRADE_ACTION_DEAL request.type=ORDER_TYPE_BUY "
                    "request.symbol=EURUSD request.volume=0.01000000 "
                    "request.price=1.10000000 request.sl=1.09900000 "
                    "request.tp=1.10200000 request.deviation=10 "
                    "request.type_filling=ORDER_FILLING_FOK SYMBOL_FILLING_MODE=2"
                ),
                (
                    "TESTER_EXECUTION_ORDER_REJECTED retcode=10030 "
                    "comment=Unsupported filling mode no retry for this signal"
                ),
                (
                    "TESTER_EXECUTION_SUMMARY "
                    "tester_entry_intents_received=40 "
                    "tester_orders_attempted=40 "
                    "tester_orders_sent_success=0 "
                    "tester_orders_rejected=40 "
                    "tester_orders_skipped_by_gate=0 "
                    "top_tester_gate_failures=SLTP:0 "
                    "last_tester_gate_failure=none event=OnTester"
                ),
            ]
        ),
        encoding="utf-8",
    )

    result = parse_strategy_tester_report(report, monitor_only=False)

    assert result.status == "PASS"
    assert result.diagnostics_assessment == "tester orders attempted but report shows zero trades"
    assert result.tester_execution_summary["rejection_retcode_counts"]["10030"] == 2
    assert result.tester_execution_summary["rejection_comment_counts"][
        "Unsupported filling mode"
    ] == 2
    assert "tester rejection retcodes: 10030=2" in result.message


def test_no_new_order_call_locations_for_phase14_4() -> None:
    for path in MQL5_ROOT.rglob("*"):
        if path.suffix.lower() not in {".mq5", ".mqh"} or path in {
            TRIAL_EXECUTION,
            TESTER_EXECUTION,
        }:
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

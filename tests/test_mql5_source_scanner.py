from __future__ import annotations

from pathlib import Path

from trading_bot.mql5.source_scan import scan_mql5_source_tree


def _write_minimal_safe_tree(root: Path) -> None:
    ea = root / "mql5" / "Experts" / "UpcomersNYSessionPropBot" / "UpcomersNYSessionPropBot.mq5"
    tm = root / "mql5" / "Include" / "UpcomersNYSessionPropBot" / "TradeManager.mqh"
    include = root / "mql5" / "Include" / "UpcomersNYSessionPropBot"
    ea.parent.mkdir(parents=True)
    tm.parent.mkdir(parents=True)
    ea.write_text(
        "\n".join(
            [
                "input bool EnableTrading = false;",
                "input bool EnableTrialExecution = false;",
                "input bool StrategyTesterExecutionMode = false;",
                "input bool EnablePropChallengeMode = false;",
                "input ENUM_UPCOMERS_ACCOUNT_PROGRAM AccountProgram = "
                "ACCOUNT_PROGRAM_TRIAL_RISK_FREE;",
                "input bool RequireManualConfirmationText = true;",
                "input int MinHoldSeconds = 180;",
                "input double MaxDailyLossHardPct = 3.0;",
                "input double MaxOverallLossHardPct = 6.0;",
                "input double MaxRiskPerTradePct = 0.50;",
                "input bool StopLossRequired = true;",
                "input int MaxTradesPerDay = 1;",
                "input int MaxServerMessagesPerDay = 500;",
                "input int MaxOpenPositionsTotal = 1;",
                'input string AllowedSymbols = "EURUSD";',
                "input ENUM_UPCOMERS_BROKER_TIME_MODE BrokerTimeMode = "
                "BROKER_TIME_MANUAL_UTC_OFFSET;",
                "input int BrokerServerUtcOffsetMinutes = 0;",
                "input bool RequireBrokerTimeValidation = true;",
                "input bool UseSpreadFilter = true;",
                "input int MaxSpreadPoints = 30;",
                "input bool SpreadUnknownBlocksTrading = true;",
                "input ENUM_UPCOMERS_EVALUATION_MODE EvaluationMode = "
                "EVALUATION_ON_NEW_CLOSED_BAR;",
                "input int MinEvaluationSeconds = 60;",
                "enum ENUM_UPCOMERS_SIGNAL {",
                "SIGNAL_WAIT, SIGNAL_SETUP_FORMING, SIGNAL_ENTER_LONG_INTENT,",
                "SIGNAL_ENTER_SHORT_INTENT, SIGNAL_EXIT_INTENT, SIGNAL_SKIP_SESSION,",
                "SIGNAL_SKIP_SPREAD, SIGNAL_SKIP_NEWS, SIGNAL_SKIP_DATA,",
                "SIGNAL_SESSION_CLOSE };",
                "string marker = \"EntryIntentHasRequiredStopLoss SuggestedStopLoss\";",
                "string marker2 = \"SetEntryIntentDecision IsEntrySessionForSymbol\";",
                "string marker3 = \"ORB_SIGNAL_COOLDOWN VWAP_SIGNAL_COOLDOWN\";",
                "string marker4 = \"manualconfirmation accountstage isprotectedaccountstage\";",
                "string marker5 = \"trialevidenceid sourcescanpassid compilepassid\";",
                "string marker6 = \"finalauditpackageid humanapprovalid\";",
                "string marker7 = \"propdayresettimezone dynamicriskshield\";",
                "string marker8 = \"unknown_rule_block stoplossrequired maxtradesperday\";",
                "string marker9 = \"recordtradeactionrequest maxservermessagesperday\";",
                "string marker10 = \"maxdailyloss maxoverallloss\";",
                "string marker11 = \"validatephase5complianceconfig\";",
                "string marker12 = \"TradeManager refuses execution no-trade\";",
                "string marker12b = \"ValidateTrialExecutionConfig TrialRiskFree "
                "I_ACCEPT_TRIAL_RISK_FREE_EXECUTION_ONLY AllowedSymbols\";",
                "input int MaxSignalsPerStrategyPerSession = 1;",
                "string marker13 = \"SPREAD_BLOCK THROTTLE_ON_NEW_CLOSED_BAR\";",
                "string marker14 = \"IsFxGoldCryptoNYSession\";",
                "string marker15 = \"UPCOMERS_NY_INDEX_CASH_START_MINUTE 570\";",
                (
                    "string marker16 = \"WAIT/skip/setup evaluations do not count as "
                    "trade attempts or server messages\";"
                ),
            ]
        ),
        encoding="utf-8",
    )
    tm.write_text(
        "class CMonitorTradeManager {\n"
        "bool RefuseExecution() { string s = \"no-trade TradeManager\"; return false; }\n"
        "};\n",
        encoding="utf-8",
    )
    (include / "TrialExecution.mqh").write_text(
        "\n".join(
            [
                "bool ProcessDecision() {",
                "ValidateTrialExecutionConfig(config, reason);",
                "ACCOUNT_PROGRAM_TRIAL_RISK_FREE;",
                "ACCOUNT_STAGE_TRIAL;",
                "EnableTrialExecution;",
                "EnableTrading;",
                "EnablePropChallengeMode;",
                "HasTrialExecutionConfirmation(config);",
                "SourceScanPassId;",
                "StopLossRequired;",
                "MinHoldSeconds;",
                "MaxRiskPerTradePct;",
                "RiskPerTradePct;",
                "MaxOpenPositionsTotal;",
                "MaxOpenPositionsPerSymbol;",
                "MaxTradesPerDay;",
                "MaxServerMessagesPerDay;",
                "AllowedSymbols;",
                "UseSpreadFilter;",
                "RequireBrokerTimeValidation;",
                "BrokerTimeValidationNote;",
                "MaxSpreadPoints;",
                "HasStopLoss;",
                "HasTakeProfit;",
                "SYMBOL_TRADE_STOPS_LEVEL;",
                "SYMBOL_POINT;",
                "STOP_LEVEL_CONSTRAINT;",
                "TRADE_ACTION_DEAL;",
                "NO_RETRY_ORDER_SEND_ONCE;",
                "NO_ACTION_SIGNAL_NOT_EXECUTABLE;",
                "ARMED_TRIAL_EXECUTION_WAITING_FOR_VALID_SIGNAL;",
                "OrderSend(request, result);",
                "}",
            ]
        ),
        encoding="utf-8",
    )
    (include / "TesterExecution.mqh").write_text(
        "\n".join(
            [
                "bool ProcessDecision() {",
                "ValidateStrategyTesterExecutionConfig(config, isStrategyTesterRuntime, reason);",
                "TESTER_EXECUTION_SUMMARY;",
                "TESTER_GATE_FAIL_Spread;",
                "TESTER_ENTRY_INTENT_RECEIVED;",
                "TESTER_ORDER_REQUEST;",
                "TESTER_ORDER_NORMALIZED;",
                "VOLUME_NORMALIZED_TO_MIN_STEP;",
                "SYMBOL_FILLING_MODE;",
                "request.type_filling = ORDER_FILLING_IOC;",
                "TESTER_EXECUTION_ORDER_REJECTED;",
                "MQL_TESTER;",
                "StrategyTesterExecutionMode;",
                "EnableTradingInputFalse;",
                "EnableTrialExecutionFalse;",
                "EnablePropChallengeModeFalse;",
                "ACCOUNT_PROGRAM_TRIAL_RISK_FREE;",
                "ACCOUNT_STAGE_MONITOR_ONLY;",
                "AllowedSymbols;",
                "StopLossRequired;",
                "MinHoldSeconds;",
                "UseSpreadFilter;",
                "MaxSpreadPoints;",
                "HasStopLoss;",
                "HasTakeProfit;",
                "SYMBOL_TRADE_STOPS_LEVEL;",
                "SYMBOL_POINT;",
                "STOP_LEVEL_CONSTRAINT;",
                "TRADE_ACTION_DEAL;",
                "TESTER_NO_RETRY_ORDER_SEND_ONCE;",
                "TESTER_NO_ACTION_SIGNAL_NOT_EXECUTABLE;",
                "OrderSend(request, result);",
                "}",
            ]
        ),
        encoding="utf-8",
    )
    (include / "SessionManager.mqh").write_text(
        (
            "bool TryConvertBrokerServerToNewYork() { return true; }\n"
            "bool ConvertBrokerServerToUtc() { return true; }\n"
            "bool ConvertUtcToNewYork() { return true; }\n"
            "bool IsNewYorkDaylightSavingUtc() { return true; }\n"
            "int NewYorkUtcOffsetMinutesForUtc() { return -240; }\n"
            "int NthSundayOfMonth() { return 8; }\n"
        ),
        encoding="utf-8",
    )
    strategy_markers = {
        "OpeningRangeBreakout.mqh": (
            "int UPCOMERS_CLOSED_BAR_SHIFT = 1; ENUM_TIMEFRAMES tf = PERIOD_M1; "
            "string s = \"OpeningRangeMinutesToM1Bars closed M1 bars BreakThenRetest "
            "RETEST_PASS RETEST_FAIL BREAK_CLOSE_OUTSIDE\";"
        ),
        "VWAPTrendContinuation.mqh": (
            "int UPCOMERS_CLOSED_BAR_SHIFT = 1; ENUM_TIMEFRAMES tf = PERIOD_M5; "
            "string s = \"impulseAtrMultiple PULLBACK_NEAR_VWAP REJECTION_CLOSE_OK VWAP_SLOPE_OK\";"
        ),
        "NoiseBandMomentum.mqh": "int UPCOMERS_CLOSED_BAR_SHIFT = 1;",
        "LondonNYOverlapMomentum.mqh": "int UPCOMERS_CLOSED_BAR_SHIFT = 1;",
        "VolatilityExpansion.mqh": (
            "int UPCOMERS_CLOSED_BAR_SHIFT = 1; "
            "string s = \"REAL_VOLUME_USED TICK_VOLUME_USED MedianVolume VolumeTypeUsed\";"
        ),
    }
    for filename, text in strategy_markers.items():
        (include / filename).write_text(text, encoding="utf-8")


def test_scanner_catches_unsafe_mql5_order_calls(tmp_path: Path) -> None:
    _write_minimal_safe_tree(tmp_path)
    unsafe = tmp_path / "mql5" / "Experts" / "Unsafe.mq5"
    unsafe.write_text("void OnTick() { OrderSend(request, result); }\n", encoding="utf-8")

    result = scan_mql5_source_tree(tmp_path)

    assert result.status == "FAIL"
    assert {violation["pattern"] for violation in result.violations} >= {"mql5_order_send"}


def test_scanner_catches_banned_terms(tmp_path: Path) -> None:
    _write_minimal_safe_tree(tmp_path)
    unsafe = tmp_path / "mql5" / "Experts" / "Unsafe.mq5"
    unsafe.write_text('string mode = "martingale grid";\n', encoding="utf-8")

    result = scan_mql5_source_tree(tmp_path)

    patterns = {violation["pattern"] for violation in result.violations}
    assert result.status == "FAIL"
    assert {"martingale", "grid_trading"} <= patterns


def test_scanner_validates_required_numeric_and_boolean_guards(tmp_path: Path) -> None:
    _write_minimal_safe_tree(tmp_path)
    ea = tmp_path / "mql5" / "Experts" / "UpcomersNYSessionPropBot" / "UpcomersNYSessionPropBot.mq5"
    text = ea.read_text(encoding="utf-8").replace(
        "input int MinHoldSeconds = 180;",
        "input int MinHoldSeconds = 60;",
    )
    ea.write_text(text, encoding="utf-8")

    result = scan_mql5_source_tree(tmp_path)

    checks = {check.name: check for check in result.safeguards}
    assert result.status == "FAIL"
    assert checks["MinHoldSeconds"].status == "FAIL"


def test_current_repo_mql5_scanner_passes() -> None:
    result = scan_mql5_source_tree(Path(__file__).resolve().parents[1])

    assert result.status == "PASS"
    assert result.violations == []

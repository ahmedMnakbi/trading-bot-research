#property strict
#property version   "0.13"
#property description "Phase 13 Trial Risk-Free micro execution is disabled by default and not prop challenge approval."

#include "..\\..\\Include\\UpcomersNYSessionPropBot\\Config.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\Logger.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\RiskManager.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\PropFirmRules.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\SessionManager.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\SymbolManager.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\StrategyBase.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\StrategyDiagnostics.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\OpeningRangeBreakout.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\VWAPTrendContinuation.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\NoiseBandMomentum.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\LondonNYOverlapMomentum.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\VolatilityExpansion.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\NYM15SweepReclaim.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\TradeManager.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\TrialExecution.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\TesterExecution.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\StateManager.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\AuditLogger.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\MessageCounter.mqh"
#include "..\\..\\Include\\UpcomersNYSessionPropBot\\NewsFilterPlaceholder.mqh"

input bool EnableTrading = false;
input bool EnableTrialExecution = false;
input bool StrategyTesterExecutionMode = false;
input bool EnablePropChallengeMode = false;
input ENUM_UPCOMERS_ACCOUNT_PROGRAM AccountProgram = ACCOUNT_PROGRAM_TRIAL_RISK_FREE;
input ENUM_UPCOMERS_ACCOUNT_STAGE AccountStage = ACCOUNT_STAGE_MONITOR_ONLY;
input bool RequireManualConfirmationText = true;
input string ManualConfirmationText = "";
input string AccountProgramRulesReviewId = "";
input string TrialEvidenceId = "";
input string SourceScanPassId = "";
input string CompilePassId = "";
input string FinalAuditPackageId = "";
input string HumanApprovalId = "";
input string PropDayResetTimezone = UPCOMERS_UNCONFIRMED_PROP_DAY_RESET_TIMEZONE;
input string PropDayResetTimezoneConfirmationId = "";
input string DynamicRiskShieldConfirmationId = "";
input double MaxDailyLossSoftPct = 2.5;
input double MaxDailyLossHardPct = 3.0;
input double MaxOverallLossSoftPct = 5.0;
input double MaxOverallLossHardPct = 6.0;
input double RiskPerTradePct = 0.25;
input double MaxRiskPerTradePct = 0.50;
input int MaxTradesPerDay = 1;
input int MaxServerMessagesPerDay = 500;
input int MinHoldSeconds = 180;
input bool StopLossRequired = true;
input int MaxOpenPositionsTotal = 1;
input int MaxOpenPositionsPerSymbol = 1;
input string AllowedSymbols = "EURUSD";
input int TrialExecutionMagicNumber = 26060113;
input bool AllowGrid = false;
input bool AllowMartingale = false;
input bool AllowAveragingDown = false;
input bool AllowHFT = false;
input bool AllowArbitrage = false;
input bool AllowCopyTrading = false;
input bool AllowScalpingUnder2Minutes = false;
input ENUM_UPCOMERS_STRATEGY StrategySelection = STRATEGY_OPENING_RANGE_BREAKOUT;
input ENUM_TIMEFRAMES StrategyTimeframe = PERIOD_M1;
input int OpeningRangeMinutes = 15;
input double OpeningRangeMinRangePoints = 10.0;
input double OpeningRangeTakeProfitR = 2.0;
input int VWAPLookbackBars = 30;
input double VWAPStopBufferPoints = 20.0;
input int NYM15SRNYOpenHour = 9;
input int NYM15SRNYOpenMinute = 30;
input int NYM15SRNYWindowEndHour = 11;
input int NYM15SRNYWindowEndMinute = 0;
input int NYM15SREMAPeriod = 50;
input double NYM15SRMinCRTRangePoints = 100.0;
input double NYM15SRMinSweepPoints = 20.0;
input double NYM15SRStopBufferPoints = 50.0;
input double NYM15SRTakeProfitR = 2.0;
input int NYM15SRMaxBarsAfterSweep = 12;
input bool NYM15SRRequireM15DirectionAgreement = true;
input bool NYM15SRRequireReclaimBreakoutEntry = true;
input int StrategySignalCooldownSeconds = 900;
input int MaxSignalsPerStrategyPerSession = 1;
input ENUM_UPCOMERS_BROKER_TIME_MODE BrokerTimeMode = BROKER_TIME_MANUAL_UTC_OFFSET;
input int BrokerServerUtcOffsetMinutes = 0;
input bool RequireBrokerTimeValidation = true;
input string BrokerTimeValidationNote = "";
input int MaxSpreadPoints = 30;
input bool UseSpreadFilter = true;
input bool SpreadUnknownBlocksTrading = true;
input ENUM_UPCOMERS_EVALUATION_MODE EvaluationMode = EVALUATION_ON_NEW_CLOSED_BAR;
input int MinEvaluationSeconds = 60;
input bool LogThrottleSkips = false;

SUpcomersConfig g_config;
CUpcomersLogger g_logger;
CAuditLogger g_audit;
CMessageCounter g_messageCounter;
CStateManager g_state;
CStrategyDiagnostics g_strategyDiagnostics;
CSessionManager g_sessionManager;
CSymbolManager g_symbolManager;
CRiskManager g_riskManager;
CPropFirmRules g_propFirmRules;
CMonitorTradeManager g_tradeManager;
CTrialExecutionManager g_trialExecution;
CTesterExecutionManager g_testerExecution;
CNewsFilterPlaceholder g_newsFilter;
COpeningRangeBreakoutStrategy g_openingRange;
CVWAPTrendContinuationStrategy g_vwapTrend;
CNoiseBandMomentumStrategy g_noiseBand;
CLondonNYOverlapMomentumStrategy g_overlapMomentum;
CVolatilityExpansionStrategy g_volatilityExpansion;
CNYm15SweepReclaimStrategy g_nyM15SweepReclaim;

void LoadInputConfiguration()
{
   g_config.EnableTrading = EnableTrading;
   g_config.EnableTrialExecution = EnableTrialExecution;
   g_config.StrategyTesterExecutionMode = StrategyTesterExecutionMode;
   g_config.EnablePropChallengeMode = EnablePropChallengeMode;
   g_config.AccountProgram = AccountProgram;
   g_config.AccountStage = AccountStage;
   g_config.RequireManualConfirmationText = RequireManualConfirmationText;
   g_config.ManualConfirmationText = ManualConfirmationText;
   g_config.AccountProgramRulesReviewId = AccountProgramRulesReviewId;
   g_config.TrialEvidenceId = TrialEvidenceId;
   g_config.SourceScanPassId = SourceScanPassId;
   g_config.CompilePassId = CompilePassId;
   g_config.FinalAuditPackageId = FinalAuditPackageId;
   g_config.HumanApprovalId = HumanApprovalId;
   g_config.PropDayResetTimezone = PropDayResetTimezone;
   g_config.PropDayResetTimezoneConfirmationId = PropDayResetTimezoneConfirmationId;
   g_config.DynamicRiskShieldConfirmationId = DynamicRiskShieldConfirmationId;
   g_config.MaxDailyLossSoftPct = MaxDailyLossSoftPct;
   g_config.MaxDailyLossHardPct = MaxDailyLossHardPct;
   g_config.MaxOverallLossSoftPct = MaxOverallLossSoftPct;
   g_config.MaxOverallLossHardPct = MaxOverallLossHardPct;
   g_config.RiskPerTradePct = RiskPerTradePct;
   g_config.MaxRiskPerTradePct = MaxRiskPerTradePct;
   g_config.MaxTradesPerDay = MaxTradesPerDay;
   g_config.MaxServerMessagesPerDay = MaxServerMessagesPerDay;
   g_config.MinHoldSeconds = MinHoldSeconds;
   g_config.StopLossRequired = StopLossRequired;
   g_config.MaxOpenPositionsTotal = MaxOpenPositionsTotal;
   g_config.MaxOpenPositionsPerSymbol = MaxOpenPositionsPerSymbol;
   g_config.AllowedSymbols = AllowedSymbols;
   g_config.TrialExecutionMagicNumber = TrialExecutionMagicNumber;
   g_config.AllowGrid = AllowGrid;
   g_config.AllowMartingale = AllowMartingale;
   g_config.AllowAveragingDown = AllowAveragingDown;
   g_config.AllowHFT = AllowHFT;
   g_config.AllowArbitrage = AllowArbitrage;
   g_config.AllowCopyTrading = AllowCopyTrading;
   g_config.AllowScalpingUnder2Minutes = AllowScalpingUnder2Minutes;
   g_config.BrokerTimeMode = BrokerTimeMode;
   g_config.BrokerServerUtcOffsetMinutes = BrokerServerUtcOffsetMinutes;
   g_config.RequireBrokerTimeValidation = RequireBrokerTimeValidation;
   g_config.BrokerTimeValidationNote = BrokerTimeValidationNote;
   g_config.MaxSpreadPoints = MaxSpreadPoints;
   g_config.UseSpreadFilter = UseSpreadFilter;
   g_config.SpreadUnknownBlocksTrading = SpreadUnknownBlocksTrading;
   g_config.EvaluationMode = EvaluationMode;
   g_config.MinEvaluationSeconds = MinEvaluationSeconds;
   g_config.LogThrottleSkips = LogThrottleSkips;
}

bool IsStrategyTesterRuntime()
{
   return (MQLInfoInteger(MQL_TESTER) != 0);
}

void LogStrategyDiagnosticsSummary(const string eventName)
{
   if(!IsStrategyTesterRuntime() && !g_config.StrategyTesterExecutionMode)
      return;
   g_logger.Warn(
      "StrategyDiagnostics",
      g_strategyDiagnostics.Summary(
         EnumToString(StrategySelection),
         g_config.StrategyTesterExecutionMode,
         IsStrategyTesterRuntime(),
         eventName
      )
   );
   g_logger.Warn("TesterExecution", g_testerExecution.Summary(eventName));
}

string GateTextOrEmpty(const string value)
{
   return HasText(value) ? value : "<empty>";
}

string GateIntText(const int value)
{
   return IntegerToString(value);
}

string GateDoubleText(const double value)
{
   return DoubleToString(value, 2);
}

void LogStartupGateFailure(
   const string gateName,
   const string inputValue,
   const string expectedValue,
   const string appliesTo
)
{
   g_logger.Error(
      "ConfigGate",
      StringFormat(
         "GATE_FAIL_%s input_value=%s expected_value=%s applies_to=%s",
         gateName,
         inputValue,
         expectedValue,
         appliesTo
      )
   );
}

void LogStartupGateIfFalse(
   const string gateName,
   const bool passed,
   const string inputValue,
   const string expectedValue,
   const string appliesTo
)
{
   if(!passed)
      LogStartupGateFailure(gateName, inputValue, expectedValue, appliesTo);
}

void LogProtectedMetadataGateFailures(
   const SUpcomersConfig &config,
   const string appliesTo
)
{
   LogStartupGateIfFalse(
      "ACCOUNT_PROGRAM_RULES_REVIEW_ID",
      HasText(config.AccountProgramRulesReviewId),
      GateTextOrEmpty(config.AccountProgramRulesReviewId),
      "non-empty current rules review ID",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_EVIDENCE_ID",
      HasText(config.TrialEvidenceId),
      GateTextOrEmpty(config.TrialEvidenceId),
      "non-empty Trial evidence ID",
      appliesTo
   );
   LogStartupGateIfFalse(
      "SOURCE_SCAN_PASS_ID",
      HasText(config.SourceScanPassId),
      GateTextOrEmpty(config.SourceScanPassId),
      "non-empty source scan PASS ID",
      appliesTo
   );
   LogStartupGateIfFalse(
      "COMPILE_PASS_ID",
      HasText(config.CompilePassId),
      GateTextOrEmpty(config.CompilePassId),
      "non-empty compile PASS ID",
      appliesTo
   );
   LogStartupGateIfFalse(
      "FINAL_AUDIT_PACKAGE_ID",
      HasText(config.FinalAuditPackageId),
      GateTextOrEmpty(config.FinalAuditPackageId),
      "non-empty final audit package ID",
      appliesTo
   );
   LogStartupGateIfFalse(
      "HUMAN_APPROVAL_ID",
      HasText(config.HumanApprovalId),
      GateTextOrEmpty(config.HumanApprovalId),
      "non-empty explicit human approval ID",
      appliesTo
   );
   LogStartupGateIfFalse(
      "PROP_DAY_RESET_TIMEZONE_CONFIRMATION_ID",
      HasText(config.PropDayResetTimezoneConfirmationId),
      GateTextOrEmpty(config.PropDayResetTimezoneConfirmationId),
      "non-empty prop day reset timezone confirmation ID",
      appliesTo
   );
   LogStartupGateIfFalse(
      "DYNAMIC_RISK_SHIELD_CONFIRMATION_ID",
      HasText(config.DynamicRiskShieldConfirmationId),
      GateTextOrEmpty(config.DynamicRiskShieldConfirmationId),
      "non-empty Dynamic Risk Shield confirmation ID",
      appliesTo
   );
}

void LogTrialMicroExecutionGateFailures(const SUpcomersConfig &config)
{
   if(!config.EnableTrialExecution)
      return;

   const string appliesTo = "TrialRiskFreeMicroExecution";
   LogStartupGateIfFalse(
      "TRIAL_ENABLE_TRADING",
      config.EnableTrading,
      BoolToText(config.EnableTrading),
      "true",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_ENABLE_EXECUTION",
      config.EnableTrialExecution,
      BoolToText(config.EnableTrialExecution),
      "true",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_PROP_CHALLENGE_MODE",
      !config.EnablePropChallengeMode,
      BoolToText(config.EnablePropChallengeMode),
      "false",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_ACCOUNT_PROGRAM",
      config.AccountProgram == ACCOUNT_PROGRAM_TRIAL_RISK_FREE,
      AccountProgramToString(config.AccountProgram),
      "TrialRiskFree",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_ACCOUNT_STAGE",
      config.AccountStage == ACCOUNT_STAGE_TRIAL,
      AccountStageToString(config.AccountStage),
      "Trial",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_MANUAL_CONFIRMATION_TEXT",
      HasTrialExecutionConfirmation(config),
      GateTextOrEmpty(config.ManualConfirmationText),
      UPCOMERS_TRIAL_EXECUTION_CONFIRMATION_TEXT,
      appliesTo
   );
   LogStartupGateIfFalse(
      "SOURCE_SCAN_PASS_ID",
      HasText(config.SourceScanPassId),
      GateTextOrEmpty(config.SourceScanPassId),
      "non-empty source scan PASS ID",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_ALLOWED_SYMBOLS",
      IsTrialExecutionSymbolSetStrict(config.AllowedSymbols),
      GateTextOrEmpty(config.AllowedSymbols),
      "EURUSD",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_MAX_TRADES_PER_DAY",
      config.MaxTradesPerDay == 1,
      GateIntText(config.MaxTradesPerDay),
      "1",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_MAX_OPEN_POSITIONS_TOTAL",
      config.MaxOpenPositionsTotal == 1,
      GateIntText(config.MaxOpenPositionsTotal),
      "1",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_MAX_OPEN_POSITIONS_PER_SYMBOL",
      config.MaxOpenPositionsPerSymbol == 1,
      GateIntText(config.MaxOpenPositionsPerSymbol),
      "1",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_STOP_LOSS_REQUIRED",
      config.StopLossRequired,
      BoolToText(config.StopLossRequired),
      "true",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_MIN_HOLD_SECONDS",
      config.MinHoldSeconds >= 180,
      GateIntText(config.MinHoldSeconds),
      ">=180",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_RISK_PER_TRADE_PCT",
      config.RiskPerTradePct <= 0.25,
      GateDoubleText(config.RiskPerTradePct),
      "<=0.25",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_MAX_RISK_PER_TRADE_PCT",
      config.MaxRiskPerTradePct <= 0.50,
      GateDoubleText(config.MaxRiskPerTradePct),
      "<=0.50",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_MAX_SERVER_MESSAGES_PER_DAY",
      config.MaxServerMessagesPerDay > 0 && config.MaxServerMessagesPerDay <= 500,
      GateIntText(config.MaxServerMessagesPerDay),
      "1..500",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_USE_SPREAD_FILTER",
      config.UseSpreadFilter,
      BoolToText(config.UseSpreadFilter),
      "true",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TRIAL_REQUIRE_BROKER_TIME_VALIDATION",
      config.RequireBrokerTimeValidation,
      BoolToText(config.RequireBrokerTimeValidation),
      "true",
      appliesTo
   );
   LogStartupGateIfFalse(
      "BROKER_TIME_VALIDATION_NOTE",
      HasText(config.BrokerTimeValidationNote),
      GateTextOrEmpty(config.BrokerTimeValidationNote),
      "non-empty note confirming BrokerServerUtcOffsetMinutes",
      appliesTo
   );
}

void LogStrategyTesterExecutionGateFailures(
   const SUpcomersConfig &config,
   const bool isStrategyTesterRuntime
)
{
   if(!config.StrategyTesterExecutionMode)
      return;

   const string appliesTo = "StrategyTesterSimulatedExecutionOnly";
   LogStartupGateIfFalse(
      "TESTER_RUNTIME",
      isStrategyTesterRuntime,
      BoolToText(isStrategyTesterRuntime),
      "true from MQL_TESTER",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TESTER_EXECUTION_MODE",
      config.StrategyTesterExecutionMode,
      BoolToText(config.StrategyTesterExecutionMode),
      "true",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TESTER_ENABLE_TRADING_INPUT",
      !config.EnableTrading,
      BoolToText(config.EnableTrading),
      "false",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TESTER_ENABLE_TRIAL_EXECUTION",
      !config.EnableTrialExecution,
      BoolToText(config.EnableTrialExecution),
      "false",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TESTER_PROP_CHALLENGE_MODE",
      !config.EnablePropChallengeMode,
      BoolToText(config.EnablePropChallengeMode),
      "false",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TESTER_ACCOUNT_PROGRAM",
      config.AccountProgram == ACCOUNT_PROGRAM_TRIAL_RISK_FREE,
      AccountProgramToString(config.AccountProgram),
      "TrialRiskFree",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TESTER_ACCOUNT_STAGE",
      config.AccountStage == ACCOUNT_STAGE_MONITOR_ONLY,
      AccountStageToString(config.AccountStage),
      "MonitorOnly",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TESTER_ALLOWED_SYMBOLS",
      IsStrategyTesterResearchSymbolAllowed(config.AllowedSymbols),
      GateTextOrEmpty(config.AllowedSymbols),
      "EURUSD|NACUSD.c|SPCUSD.c",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TESTER_STOP_LOSS_REQUIRED",
      config.StopLossRequired,
      BoolToText(config.StopLossRequired),
      "true",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TESTER_MIN_HOLD_SECONDS",
      config.MinHoldSeconds >= 180,
      GateIntText(config.MinHoldSeconds),
      ">=180",
      appliesTo
   );
   LogStartupGateIfFalse(
      "TESTER_USE_SPREAD_FILTER",
      config.UseSpreadFilter,
      BoolToText(config.UseSpreadFilter),
      "true",
      appliesTo
   );
}

void LogStartupValidationGateFailures(const SUpcomersConfig &config)
{
   LogStartupGateIfFalse(
      "ACCOUNT_PROGRAM_SUPPORTED",
      IsKnownAccountProgram(config.AccountProgram),
      AccountProgramToString(config.AccountProgram),
      "TrialRiskFree|Vanguard|Surge2Step|Custom",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "ACCOUNT_STAGE_SUPPORTED",
      IsKnownAccountStage(config.AccountStage),
      AccountStageToString(config.AccountStage),
      "MonitorOnly|Trial|Challenge|Verification|Funded",
      "AllModes"
   );

   bool isStrategyTesterRuntime = IsStrategyTesterRuntime();
   LogTrialMicroExecutionGateFailures(config);
   LogStrategyTesterExecutionGateFailures(config, isStrategyTesterRuntime);

   if(config.EnableTrading && !config.EnableTrialExecution &&
      !config.StrategyTesterExecutionMode)
   {
      LogStartupGateIfFalse(
         "MANUAL_CONFIRMATION_TEXT",
         config.RequireManualConfirmationText &&
         config.ManualConfirmationText == UPCOMERS_REQUIRED_CONFIRMATION_TEXT,
         GateTextOrEmpty(config.ManualConfirmationText),
         UPCOMERS_REQUIRED_CONFIRMATION_TEXT,
         "NonTrialTradingBlocked"
      );
   }

   if(config.EnablePropChallengeMode)
      LogProtectedMetadataGateFailures(config, "ProtectedStagesOnly");

   if(IsRuleUnverifiedAccountProgram(config.AccountProgram) &&
      (config.EnableTrading || config.EnablePropChallengeMode ||
       config.StrategyTesterExecutionMode ||
       IsProtectedAccountStage(config.AccountStage)))
   {
      LogStartupGateFailure(
         "ACCOUNT_PROGRAM_RULE_VERIFIED",
         AccountProgramToString(config.AccountProgram),
         "current exact rules encoded before active or protected use",
         "Surge2StepCustomProtectedUse"
      );
   }

   if(config.AccountProgram == ACCOUNT_PROGRAM_VANGUARD &&
      (config.EnableTrading || config.EnablePropChallengeMode ||
       config.StrategyTesterExecutionMode ||
       IsProtectedAccountStage(config.AccountStage)))
   {
      LogProtectedMetadataGateFailures(config, "VanguardProtectedUse");
   }

   if(IsProtectedAccountStage(config.AccountStage))
      LogProtectedMetadataGateFailures(config, "ProtectedStagesOnly");

   LogStartupGateIfFalse(
      "MAX_DAILY_LOSS_HARD_PCT",
      config.MaxDailyLossHardPct < 4.0,
      GateDoubleText(config.MaxDailyLossHardPct),
      "<4.00",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "MAX_OVERALL_LOSS_HARD_PCT",
      config.MaxOverallLossHardPct < 7.0,
      GateDoubleText(config.MaxOverallLossHardPct),
      "<7.00",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "DAILY_SOFT_BELOW_HARD",
      config.MaxDailyLossSoftPct < config.MaxDailyLossHardPct,
      GateDoubleText(config.MaxDailyLossSoftPct) + "/" + GateDoubleText(config.MaxDailyLossHardPct),
      "soft<hard",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "OVERALL_SOFT_BELOW_HARD",
      config.MaxOverallLossSoftPct < config.MaxOverallLossHardPct,
      GateDoubleText(config.MaxOverallLossSoftPct) + "/" + GateDoubleText(config.MaxOverallLossHardPct),
      "soft<hard",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "RISK_PER_TRADE_WITHIN_MAX",
      config.RiskPerTradePct <= config.MaxRiskPerTradePct,
      GateDoubleText(config.RiskPerTradePct) + "/" + GateDoubleText(config.MaxRiskPerTradePct),
      "RiskPerTradePct<=MaxRiskPerTradePct",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "MAX_RISK_PER_TRADE_PCT",
      config.MaxRiskPerTradePct <= 0.50,
      GateDoubleText(config.MaxRiskPerTradePct),
      "<=0.50",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "MIN_HOLD_SECONDS",
      config.MinHoldSeconds >= 180,
      GateIntText(config.MinHoldSeconds),
      ">=180",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "STOP_LOSS_REQUIRED",
      config.StopLossRequired,
      BoolToText(config.StopLossRequired),
      "true",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "MAX_TRADES_PER_DAY",
      config.MaxTradesPerDay > 0 && config.MaxTradesPerDay <= 20,
      GateIntText(config.MaxTradesPerDay),
      "1..20",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "MAX_SERVER_MESSAGES_PER_DAY",
      config.MaxServerMessagesPerDay > 0 && config.MaxServerMessagesPerDay <= 2000,
      GateIntText(config.MaxServerMessagesPerDay),
      "1..2000",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "MAX_OPEN_POSITIONS_POSITIVE",
      config.MaxOpenPositionsTotal > 0 && config.MaxOpenPositionsPerSymbol > 0,
      GateIntText(config.MaxOpenPositionsTotal) + "/" + GateIntText(config.MaxOpenPositionsPerSymbol),
      "positive total/per-symbol caps",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "MAX_OPEN_POSITIONS_RELATION",
      config.MaxOpenPositionsPerSymbol <= config.MaxOpenPositionsTotal,
      GateIntText(config.MaxOpenPositionsPerSymbol) + "/" + GateIntText(config.MaxOpenPositionsTotal),
      "per-symbol<=total",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "ALLOWED_SYMBOLS_NON_EMPTY",
      HasText(config.AllowedSymbols),
      GateTextOrEmpty(config.AllowedSymbols),
      "non-empty allowed symbol list",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "TRIAL_EXECUTION_MAGIC_NUMBER",
      config.TrialExecutionMagicNumber > 0,
      GateIntText(config.TrialExecutionMagicNumber),
      ">0",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "PROHIBITED_BEHAVIOR_FLAGS",
      !config.AllowGrid && !config.AllowMartingale && !config.AllowAveragingDown &&
      !config.AllowHFT && !config.AllowArbitrage && !config.AllowCopyTrading &&
      !config.AllowScalpingUnder2Minutes,
      StringFormat(
         "config.AllowGrid=%s config.AllowMartingale=%s config.AllowAveragingDown=%s config.AllowHFT=%s config.AllowArbitrage=%s config.AllowCopyTrading=%s config.AllowScalpingUnder2Minutes=%s",
         BoolToText(config.AllowGrid),
         BoolToText(config.AllowMartingale),
         BoolToText(config.AllowAveragingDown),
         BoolToText(config.AllowHFT),
         BoolToText(config.AllowArbitrage),
         BoolToText(config.AllowCopyTrading),
         BoolToText(config.AllowScalpingUnder2Minutes)
      ),
      "all false",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "BROKER_TIME_MODE",
      config.BrokerTimeMode == BROKER_TIME_MANUAL_UTC_OFFSET,
      BrokerTimeModeToString(config.BrokerTimeMode),
      "ManualUtcOffset",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "BROKER_SERVER_UTC_OFFSET_MINUTES",
      config.BrokerServerUtcOffsetMinutes >= -720 &&
      config.BrokerServerUtcOffsetMinutes <= 840,
      GateIntText(config.BrokerServerUtcOffsetMinutes),
      "-720..840",
      "AllModes"
   );
   if(config.RequireBrokerTimeValidation && config.AccountStage != ACCOUNT_STAGE_MONITOR_ONLY)
   {
      const string appliesTo = config.EnableTrialExecution
         ? "TrialRiskFreeMicroExecution"
         : "TrialOrProtectedStages";
      LogStartupGateIfFalse(
         "BROKER_TIME_VALIDATION_NOTE",
         HasText(config.BrokerTimeValidationNote),
         GateTextOrEmpty(config.BrokerTimeValidationNote),
         "non-empty note confirming BrokerServerUtcOffsetMinutes",
         appliesTo
      );
   }
   LogStartupGateIfFalse(
      "MAX_SPREAD_POINTS",
      config.MaxSpreadPoints > 0,
      GateIntText(config.MaxSpreadPoints),
      ">0",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "SPREAD_UNKNOWN_BLOCKS_TRADING",
      config.SpreadUnknownBlocksTrading,
      BoolToText(config.SpreadUnknownBlocksTrading),
      "true",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "EVALUATION_MODE",
      config.EvaluationMode == EVALUATION_ON_NEW_CLOSED_BAR ||
      config.EvaluationMode == EVALUATION_TIMER,
      EvaluationModeToString(config.EvaluationMode),
      "OnNewClosedBar|Timer",
      "AllModes"
   );
   LogStartupGateIfFalse(
      "MIN_EVALUATION_SECONDS",
      config.MinEvaluationSeconds >= 1,
      GateIntText(config.MinEvaluationSeconds),
      ">=1",
      "AllModes"
   );
}

void EvaluateSelectedStrategy(SStrategyDecision &decision)
{
   datetime now = TimeCurrent();

   switch(StrategySelection)
   {
      case STRATEGY_OPENING_RANGE_BREAKOUT:
         g_openingRange.Evaluate(
            _Symbol,
            StrategyTimeframe,
            now,
            g_sessionManager,
            decision,
            OpeningRangeMinutes,
            OpeningRangeMinRangePoints,
            OpeningRangeTakeProfitR,
            3,
            MaxSignalsPerStrategyPerSession,
            MinHoldSeconds
         );
         return;
      case STRATEGY_VWAP_TREND_CONTINUATION:
         g_vwapTrend.Evaluate(
            _Symbol,
            StrategyTimeframe,
            now,
            g_sessionManager,
            decision,
            VWAPLookbackBars,
            VWAPStopBufferPoints,
            StrategySignalCooldownSeconds,
            MaxSignalsPerStrategyPerSession,
            MinHoldSeconds
         );
         return;
      case STRATEGY_NOISE_BAND_MOMENTUM:
         g_noiseBand.Evaluate(
            _Symbol,
            StrategyTimeframe,
            now,
            g_sessionManager,
            decision,
            MaxSignalsPerStrategyPerSession,
            MinHoldSeconds
         );
         return;
      case STRATEGY_LONDON_NY_OVERLAP_MOMENTUM:
         g_overlapMomentum.Evaluate(
            _Symbol,
            StrategyTimeframe,
            now,
            g_sessionManager,
            decision,
            MaxSignalsPerStrategyPerSession,
            MinHoldSeconds
         );
         return;
      case STRATEGY_VOLATILITY_EXPANSION:
         g_volatilityExpansion.Evaluate(
            _Symbol,
            StrategyTimeframe,
            now,
            g_sessionManager,
            decision,
            MaxSignalsPerStrategyPerSession,
            MinHoldSeconds
         );
         return;
      case STRATEGY_NY_M15_SWEEP_RECLAIM:
         g_nyM15SweepReclaim.Evaluate(
            _Symbol,
            StrategyTimeframe,
            now,
            g_sessionManager,
            decision,
            NYM15SRNYOpenHour,
            NYM15SRNYOpenMinute,
            NYM15SRNYWindowEndHour,
            NYM15SRNYWindowEndMinute,
            NYM15SREMAPeriod,
            NYM15SRMinCRTRangePoints,
            NYM15SRMinSweepPoints,
            NYM15SRStopBufferPoints,
            NYM15SRTakeProfitR,
            NYM15SRMaxBarsAfterSweep,
            NYM15SRRequireM15DirectionAgreement,
            NYM15SRRequireReclaimBreakoutEntry,
            MaxTradesPerDay,
            MinHoldSeconds
         );
         return;
   }
   SetWaitDecision(decision, "unknown strategy selection");
}

void ProcessMonitorEvent(const string eventName)
{
   string reason = "";
   datetime closedBarTime = 0;
   if(!g_state.ShouldEvaluateMonitorEvent(
      eventName,
      _Symbol,
      StrategyTimeframe,
      g_config,
      closedBarTime,
      reason
   ))
   {
      if(g_config.LogThrottleSkips)
         g_logger.Info("Throttle", reason);
      return;
   }
   g_state.MarkMonitorEvaluation(closedBarTime);

   int propDayKey = g_propFirmRules.BuildPropDayKey(TimeCurrent(), g_config.PropDayResetTimezone);
   g_messageCounter.ResetForNewPropDay(propDayKey);
   g_messageCounter.CountMonitorEvaluation();
   g_audit.LogDecision("Monitor", StringFormat("event=%s monitor-only evaluation", eventName));

   if(!g_sessionManager.CheckSession(TimeCurrent(), reason))
      g_logger.Warn("Session", reason);
   else
      g_logger.Info("Session", reason);

   if(!g_symbolManager.CheckSymbol(_Symbol, reason))
      g_logger.Warn("Symbol", reason);
   else
      g_logger.Info("Symbol", reason);

   int spreadPoints = -1;
   bool spreadOk = g_symbolManager.CheckSpread(_Symbol, g_config, spreadPoints, reason);
   if(!spreadOk)
      g_logger.Warn("Spread", reason);
   else
      g_logger.Info("Spread", reason);

   if(g_newsFilter.IsNewsBlocked(reason))
      g_logger.Warn("News", reason);
   else
      g_logger.Info("News", reason);

   if(!g_propFirmRules.CheckRules(g_config, reason))
      g_logger.Warn("PropFirmRules", reason);
   else
      g_logger.Info("PropFirmRules", reason);

   ENUM_UPCOMERS_GUARD_STATUS dailyLossStatus = g_propFirmRules.CheckDailyLossGuard(g_config, 0.0, reason);
   g_logger.Warn(
      "DailyLoss",
      StringFormat("%s: %s", GuardStatusToString(dailyLossStatus), reason)
   );

   ENUM_UPCOMERS_GUARD_STATUS overallLossStatus = g_propFirmRules.CheckOverallLossGuard(g_config, 0.0, reason);
   g_logger.Warn(
      "OverallLoss",
      StringFormat("%s: %s", GuardStatusToString(overallLossStatus), reason)
   );

   if(!g_riskManager.CheckRisk(g_config, reason))
      g_logger.Warn("Risk", reason);
   else
      g_logger.Info("Risk", reason);

   SHypotheticalTradeIntent intent;
   g_riskManager.BuildMonitorOnlyIntent(_Symbol, g_config, intent);
   if(!g_riskManager.CheckHypotheticalTradeIntent(g_config, intent, reason))
      g_logger.Warn("RiskIntent", reason);
   else
      g_logger.Info("RiskIntent", reason);

   SStrategyDecision decision;
   if(!spreadOk)
   {
      SetSkipDecision(
         decision,
         SIGNAL_SKIP_SPREAD,
         "SpreadGate",
         _Symbol,
         StrategyTimeframe,
         "SPREAD_BLOCK",
         reason,
         TimeCurrent()
      );
      datetime newYorkTime = 0;
      string timeReason = "";
      bool hasNewYorkTime = g_sessionManager.TryConvertBrokerServerToNewYork(
         TimeCurrent(),
         newYorkTime,
         timeReason
      );
      SetDecisionContext(
         decision,
         g_sessionManager.SymbolClassFor(_Symbol),
         g_sessionManager.SessionTagForSymbol(_Symbol),
         newYorkTime,
         hasNewYorkTime,
         MinHoldSeconds,
         reason,
         "VOLUME_NOT_APPLICABLE"
      );
   }
   else
   {
      EvaluateSelectedStrategy(decision);
   }
   g_audit.LogDecision(
      "Strategy",
      StringFormat(
         "Phase 9 monitor-only signal=%s strategy=%s symbol=%s reason_code=%s direction=%s stop_loss=%s quality=%.2f: %s",
         SignalToString(decision.Signal),
         decision.StrategyName,
         decision.SymbolName,
         decision.ReasonCode,
         decision.Direction,
         BoolToText(EntryIntentHasRequiredStopLoss(decision)),
         decision.QualityScore,
         decision.Reason
      )
   );
   g_audit.LogDecision(
      "StrategyDetail",
      StringFormat(
         "Phase 9 monitor-only reason_codes=%s symbol_class=%s timeframe=%s server_time=%s ny_time_available=%s session_tag=%s suggested_entry=%s suggested_sl=%s suggested_tp=%s min_hold_until=%s spread_status=%s volume_type=%s note=%s",
         decision.ReasonCodes,
         decision.SymbolClass,
         TimeframeToDecisionText(decision.Timeframe),
         TimeToString(decision.ServerTimestamp, TIME_DATE | TIME_SECONDS),
         BoolToText(decision.HasNewYorkTimestamp),
         decision.SessionTag,
         BoolToText(decision.HasSuggestedEntry),
         BoolToText(decision.HasStopLoss),
         BoolToText(decision.HasTakeProfit),
         TimeToString(decision.MinHoldUntil, TIME_DATE | TIME_SECONDS),
         decision.SpreadFilterStatus,
         decision.VolumeTypeUsed,
         decision.MonitorOnlyNote
      )
   );
   if(!EntryIntentHasRequiredStopLoss(decision))
      g_logger.Error("Strategy", "entry intent blocked because stop-loss is required");

   if(IsStrategyTesterRuntime())
      g_strategyDiagnostics.RecordDecision(decision);

   bool actionableIntent = g_messageCounter.IsActionableIntent(decision.Signal);
   if(g_config.EnableTrialExecution)
   {
      g_trialExecution.ProcessDecision(
         decision,
         _Symbol,
         g_config,
         g_messageCounter,
         g_state,
         g_logger,
         spreadPoints,
         reason
      );
      if(actionableIntent)
         g_logger.Warn("TrialExecution", reason);
   }
   else if(g_config.StrategyTesterExecutionMode && IsStrategyTesterRuntime())
   {
      int testerOrdersBefore = g_testerExecution.TesterOrdersAttempted();
      g_testerExecution.ProcessDecision(
         decision,
         _Symbol,
         g_config,
         IsStrategyTesterRuntime(),
         g_messageCounter,
         g_state,
         g_logger,
         spreadPoints,
         reason
      );
      if(g_testerExecution.TesterOrdersAttempted() > testerOrdersBefore)
         g_strategyDiagnostics.RecordTesterOrderAttempt();
      if(actionableIntent)
         g_logger.Warn("TesterExecution", reason);
   }
   else
   {
      g_tradeManager.RefuseExecution(decision, g_config, g_messageCounter, g_state, reason);
      if(actionableIntent)
         g_logger.Warn("TradeManager", reason);
   }
}

int OnInit()
{
   LoadInputConfiguration();
   g_state.Init();
   g_trialExecution.Reset();
   g_testerExecution.Reset();
   g_strategyDiagnostics.Reset();
   g_messageCounter.Reset();
   g_audit.Bind(g_logger);
   g_sessionManager.ConfigureBrokerTime(g_config);

   string reason = "";
   g_audit.LogStartupSummary(g_config);
   bool isStrategyTesterRuntime = IsStrategyTesterRuntime();
   bool configValid = ValidateRuntimeExecutionConfig(g_config, isStrategyTesterRuntime, reason);
   g_audit.LogValidationResult(configValid, reason);
   g_audit.LogUnresolvedRuleWarnings(g_config);
   if(!configValid)
   {
      g_logger.Error("ConfigGate", "INIT_PARAMETERS_INCORRECT: " + reason);
      LogStartupValidationGateFailures(g_config);
      return INIT_PARAMETERS_INCORRECT;
   }

   if(g_config.RequireManualConfirmationText)
   {
      g_logger.Info("Config", "ManualConfirmationText is required before monitor or Trial execution modes");
   }

   if(g_config.EnableTrialExecution)
   {
      g_logger.Warn(
         "Mode",
         "Trial Risk-Free micro execution mode is active only after strict gates; stop after first trade or broker rejection"
      );
   }
   else if(g_config.StrategyTesterExecutionMode)
   {
      g_logger.Warn(
         "Mode",
         "Strategy Tester simulated execution mode is active only inside MT5 Strategy Tester"
      );
   }
   else
   {
      g_logger.Info("Mode", "Monitor-only mode is active. Strategy intents are signals only.");
   }
   g_logger.Info("Mode", "EnableTrading=false and EnableTrialExecution=false remain the safe defaults.");
   g_logger.Warn(
      "Approval",
      "This EA is not approved for Surge 2 Step, Vanguard, Challenge, Verification, Funded, "
      "or live-money use"
   );
   EventSetTimer(60);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   LogStrategyDiagnosticsSummary("OnDeinit");
   EventKillTimer();
   g_logger.Info("Lifecycle", StringFormat("OnDeinit reason=%d", reason));
}

double OnTester()
{
   LogStrategyDiagnosticsSummary("OnTester");
   return 0.0;
}

void OnTick()
{
   g_state.CountTick();
   ProcessMonitorEvent("OnTick");
}

void OnTimer()
{
   g_state.CountTimer();
   ProcessMonitorEvent("OnTimer");
}

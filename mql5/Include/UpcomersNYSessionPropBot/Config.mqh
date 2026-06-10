#ifndef UPCOMERS_NY_SESSION_PROP_BOT_CONFIG_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_CONFIG_MQH

#define UPCOMERS_REQUIRED_CONFIRMATION_TEXT "I ACCEPT MONITOR ONLY PHASE 5 - NO TRADING"
#define UPCOMERS_TRIAL_EXECUTION_CONFIRMATION_TEXT "I_ACCEPT_TRIAL_RISK_FREE_EXECUTION_ONLY"
#define UPCOMERS_UNCONFIRMED_PROP_DAY_RESET_TIMEZONE "UNCONFIRMED_CONSERVATIVE"

enum ENUM_UPCOMERS_ACCOUNT_STAGE
{
   ACCOUNT_STAGE_MONITOR_ONLY = 0,
   ACCOUNT_STAGE_TRIAL = 1,
   ACCOUNT_STAGE_CHALLENGE = 2,
   ACCOUNT_STAGE_VERIFICATION = 3,
   ACCOUNT_STAGE_FUNDED = 4
};

enum ENUM_UPCOMERS_ACCOUNT_PROGRAM
{
   ACCOUNT_PROGRAM_TRIAL_RISK_FREE = 0,
   ACCOUNT_PROGRAM_VANGUARD = 1,
   ACCOUNT_PROGRAM_SURGE_2_STEP = 2,
   ACCOUNT_PROGRAM_CUSTOM = 3
};

enum ENUM_UPCOMERS_STRATEGY
{
   STRATEGY_OPENING_RANGE_BREAKOUT = 0,
   STRATEGY_VWAP_TREND_CONTINUATION = 1,
   STRATEGY_NOISE_BAND_MOMENTUM = 2,
   STRATEGY_LONDON_NY_OVERLAP_MOMENTUM = 3,
   STRATEGY_VOLATILITY_EXPANSION = 4,
   STRATEGY_NY_M15_SWEEP_RECLAIM = 5
};

enum ENUM_UPCOMERS_BROKER_TIME_MODE
{
   BROKER_TIME_MANUAL_UTC_OFFSET = 0
};

enum ENUM_UPCOMERS_EVALUATION_MODE
{
   EVALUATION_ON_NEW_CLOSED_BAR = 0,
   EVALUATION_TIMER = 1
};

enum ENUM_UPCOMERS_GUARD_STATUS
{
   GUARD_STATUS_OK = 0,
   GUARD_STATUS_SOFT_STOP = 1,
   GUARD_STATUS_HARD_STOP = 2,
   GUARD_STATUS_UNKNOWN_RULE_BLOCK = 3
};

struct SUpcomersConfig
{
   bool EnableTrading;
   bool EnableTrialExecution;
   bool StrategyTesterExecutionMode;
   bool EnablePropChallengeMode;
   ENUM_UPCOMERS_ACCOUNT_PROGRAM AccountProgram;
   ENUM_UPCOMERS_ACCOUNT_STAGE AccountStage;
   bool RequireManualConfirmationText;
   string ManualConfirmationText;
   string AccountProgramRulesReviewId;
   string TrialEvidenceId;
   string SourceScanPassId;
   string CompilePassId;
   string FinalAuditPackageId;
   string HumanApprovalId;
   string PropDayResetTimezone;
   string PropDayResetTimezoneConfirmationId;
   string DynamicRiskShieldConfirmationId;
   double MaxDailyLossSoftPct;
   double MaxDailyLossHardPct;
   double MaxOverallLossSoftPct;
   double MaxOverallLossHardPct;
   double RiskPerTradePct;
   double MaxRiskPerTradePct;
   int MaxTradesPerDay;
   int MaxServerMessagesPerDay;
   int MinHoldSeconds;
   bool StopLossRequired;
   int MaxOpenPositionsTotal;
   int MaxOpenPositionsPerSymbol;
   string AllowedSymbols;
   int TrialExecutionMagicNumber;
   bool AllowGrid;
   bool AllowMartingale;
   bool AllowAveragingDown;
   bool AllowHFT;
   bool AllowArbitrage;
   bool AllowCopyTrading;
   bool AllowScalpingUnder2Minutes;
   ENUM_UPCOMERS_BROKER_TIME_MODE BrokerTimeMode;
   int BrokerServerUtcOffsetMinutes;
   bool RequireBrokerTimeValidation;
   string BrokerTimeValidationNote;
   int MaxSpreadPoints;
   bool UseSpreadFilter;
   bool SpreadUnknownBlocksTrading;
   ENUM_UPCOMERS_EVALUATION_MODE EvaluationMode;
   int MinEvaluationSeconds;
   bool LogThrottleSkips;
};

string AccountStageToString(const ENUM_UPCOMERS_ACCOUNT_STAGE stage)
{
   switch(stage)
   {
      case ACCOUNT_STAGE_MONITOR_ONLY:
         return "MonitorOnly";
      case ACCOUNT_STAGE_TRIAL:
         return "Trial";
      case ACCOUNT_STAGE_CHALLENGE:
         return "Challenge";
      case ACCOUNT_STAGE_VERIFICATION:
         return "Verification";
      case ACCOUNT_STAGE_FUNDED:
         return "Funded";
   }
   return "Unknown";
}

string AccountProgramToString(const ENUM_UPCOMERS_ACCOUNT_PROGRAM program)
{
   switch(program)
   {
      case ACCOUNT_PROGRAM_TRIAL_RISK_FREE:
         return "TrialRiskFree";
      case ACCOUNT_PROGRAM_VANGUARD:
         return "Vanguard";
      case ACCOUNT_PROGRAM_SURGE_2_STEP:
         return "Surge2Step";
      case ACCOUNT_PROGRAM_CUSTOM:
         return "Custom";
   }
   return "Unknown";
}

string BoolToText(const bool value)
{
   return value ? "true" : "false";
}

string BrokerTimeModeToString(const ENUM_UPCOMERS_BROKER_TIME_MODE mode)
{
   switch(mode)
   {
      case BROKER_TIME_MANUAL_UTC_OFFSET:
         return "ManualUtcOffset";
   }
   return "Unknown";
}

string EvaluationModeToString(const ENUM_UPCOMERS_EVALUATION_MODE mode)
{
   switch(mode)
   {
      case EVALUATION_ON_NEW_CLOSED_BAR:
         return "OnNewClosedBar";
      case EVALUATION_TIMER:
         return "Timer";
   }
   return "Unknown";
}

string GuardStatusToString(const ENUM_UPCOMERS_GUARD_STATUS status)
{
   switch(status)
   {
      case GUARD_STATUS_OK:
         return "OK";
      case GUARD_STATUS_SOFT_STOP:
         return "SOFT_STOP";
      case GUARD_STATUS_HARD_STOP:
         return "HARD_STOP";
      case GUARD_STATUS_UNKNOWN_RULE_BLOCK:
         return "UNKNOWN_RULE_BLOCK";
   }
   return "UNKNOWN_RULE_BLOCK";
}

bool IsProtectedAccountStage(const ENUM_UPCOMERS_ACCOUNT_STAGE stage)
{
   return stage == ACCOUNT_STAGE_CHALLENGE ||
          stage == ACCOUNT_STAGE_VERIFICATION ||
          stage == ACCOUNT_STAGE_FUNDED;
}

bool IsKnownAccountStage(const ENUM_UPCOMERS_ACCOUNT_STAGE stage)
{
   return stage == ACCOUNT_STAGE_MONITOR_ONLY ||
          stage == ACCOUNT_STAGE_TRIAL ||
          stage == ACCOUNT_STAGE_CHALLENGE ||
          stage == ACCOUNT_STAGE_VERIFICATION ||
          stage == ACCOUNT_STAGE_FUNDED;
}

bool IsKnownAccountProgram(const ENUM_UPCOMERS_ACCOUNT_PROGRAM program)
{
   return program == ACCOUNT_PROGRAM_TRIAL_RISK_FREE ||
          program == ACCOUNT_PROGRAM_VANGUARD ||
          program == ACCOUNT_PROGRAM_SURGE_2_STEP ||
          program == ACCOUNT_PROGRAM_CUSTOM;
}

bool IsRuleUnverifiedAccountProgram(const ENUM_UPCOMERS_ACCOUNT_PROGRAM program)
{
   return program == ACCOUNT_PROGRAM_SURGE_2_STEP ||
          program == ACCOUNT_PROGRAM_CUSTOM;
}

bool IsProtectedAccountProgram(const ENUM_UPCOMERS_ACCOUNT_PROGRAM program)
{
   return program == ACCOUNT_PROGRAM_VANGUARD ||
          program == ACCOUNT_PROGRAM_SURGE_2_STEP ||
          program == ACCOUNT_PROGRAM_CUSTOM;
}

bool HasText(const string value)
{
   return StringLen(value) > 0;
}

bool HasRequiredProtectedStageMetadata(const SUpcomersConfig &config, string &reason)
{
   if(!HasText(config.AccountProgramRulesReviewId))
   {
      reason = "protected account program requires exact rules review ID";
      return false;
   }
   if(!HasText(config.TrialEvidenceId))
   {
      reason = "protected account stage requires trial evidence ID";
      return false;
   }
   if(!HasText(config.SourceScanPassId))
   {
      reason = "protected account stage requires source scan PASS ID";
      return false;
   }
   if(!HasText(config.CompilePassId))
   {
      reason = "protected account stage requires compile PASS ID";
      return false;
   }
   if(!HasText(config.FinalAuditPackageId))
   {
      reason = "protected account stage requires final audit package ID";
      return false;
   }
   if(!HasText(config.HumanApprovalId))
   {
      reason = "protected account stage requires explicit human approval ID";
      return false;
   }
   if(!HasText(config.PropDayResetTimezoneConfirmationId))
   {
      reason = "protected account stage requires PropDayResetTimezone confirmation ID";
      return false;
   }
   if(!HasText(config.DynamicRiskShieldConfirmationId))
   {
      reason = "protected account stage requires Dynamic Risk Shield confirmation ID";
      return false;
   }
   reason = "protected account stage metadata present";
   return true;
}

bool HasTrialExecutionConfirmation(const SUpcomersConfig &config)
{
   return config.RequireManualConfirmationText &&
          config.ManualConfirmationText == UPCOMERS_TRIAL_EXECUTION_CONFIRMATION_TEXT;
}

bool IsTrialExecutionSymbolSetStrict(const string allowedSymbols)
{
   return allowedSymbols == "EURUSD";
}

bool IsStrategyTesterResearchSymbolAllowed(const string allowedSymbols)
{
   return allowedSymbols == "EURUSD" ||
          allowedSymbols == "NACUSD.c" ||
          allowedSymbols == "SPCUSD.c";
}

bool ValidateTrialExecutionConfig(const SUpcomersConfig &config, string &reason)
{
   if(!config.EnableTrialExecution)
   {
      reason = "trial execution disabled";
      return true;
   }
   if(!config.EnableTrading)
   {
      reason = "EnableTrialExecution requires EnableTrading=true";
      return false;
   }
   if(config.EnablePropChallengeMode)
   {
      reason = "Trial execution requires EnablePropChallengeMode=false";
      return false;
   }
   if(config.AccountProgram != ACCOUNT_PROGRAM_TRIAL_RISK_FREE)
   {
      reason = "Trial execution requires AccountProgram=TrialRiskFree";
      return false;
   }
   if(config.AccountStage != ACCOUNT_STAGE_TRIAL)
   {
      reason = "Trial execution requires AccountStage=Trial";
      return false;
   }
   if(!HasTrialExecutionConfirmation(config))
   {
      reason = "Trial execution requires exact manual confirmation text";
      return false;
   }
   if(!HasText(config.SourceScanPassId))
   {
      reason = "Trial execution requires source scan PASS marker";
      return false;
   }
   if(!config.StopLossRequired)
   {
      reason = "Trial execution requires StopLossRequired=true";
      return false;
   }
   if(config.MinHoldSeconds < 180)
   {
      reason = "Trial execution requires MinHoldSeconds>=180";
      return false;
   }
   if(config.MaxRiskPerTradePct > 0.50)
   {
      reason = "Trial execution requires MaxRiskPerTradePct<=0.50";
      return false;
   }
   if(config.RiskPerTradePct > 0.25)
   {
      reason = "Trial execution requires RiskPerTradePct<=0.25";
      return false;
   }
   if(config.MaxOpenPositionsTotal != 1 || config.MaxOpenPositionsPerSymbol != 1)
   {
      reason = "Trial execution requires MaxOpenPositionsTotal=1 and MaxOpenPositionsPerSymbol=1";
      return false;
   }
   if(config.MaxTradesPerDay != 1)
   {
      reason = "Trial execution requires MaxTradesPerDay=1";
      return false;
   }
   if(config.MaxServerMessagesPerDay <= 0 || config.MaxServerMessagesPerDay > 500)
   {
      reason = "Trial execution requires MaxServerMessagesPerDay<=500";
      return false;
   }
   if(!IsTrialExecutionSymbolSetStrict(config.AllowedSymbols))
   {
      reason = "Trial execution requires AllowedSymbols=EURUSD only";
      return false;
   }
   if(!config.UseSpreadFilter)
   {
      reason = "Trial execution requires UseSpreadFilter=true";
      return false;
   }
   if(!config.RequireBrokerTimeValidation)
   {
      reason = "Trial execution requires RequireBrokerTimeValidation=true";
      return false;
   }
   if(!HasText(config.BrokerTimeValidationNote))
   {
      reason = "Trial execution requires BrokerTimeValidationNote after verifying BrokerServerUtcOffsetMinutes";
      return false;
   }
   reason = "Trial Risk-Free micro execution gates validated";
   return true;
}

bool ValidateStrategyTesterExecutionConfig(
   const SUpcomersConfig &config,
   const bool isStrategyTesterRuntime,
   string &reason
)
{
   if(!config.StrategyTesterExecutionMode)
   {
      reason = "Strategy Tester simulated execution disabled";
      return true;
   }
   if(!isStrategyTesterRuntime)
   {
      reason = "StrategyTesterExecutionMode requires MQL_TESTER runtime";
      return false;
   }
   if(config.EnableTrading)
   {
      reason = "StrategyTesterExecutionMode requires EnableTrading=false on inputs";
      return false;
   }
   if(config.EnableTrialExecution)
   {
      reason = "StrategyTesterExecutionMode is separate from EnableTrialExecution and requires EnableTrialExecution=false";
      return false;
   }
   if(config.EnablePropChallengeMode)
   {
      reason = "StrategyTesterExecutionMode requires EnablePropChallengeMode=false";
      return false;
   }
   if(config.AccountProgram != ACCOUNT_PROGRAM_TRIAL_RISK_FREE)
   {
      reason = "StrategyTesterExecutionMode requires AccountProgram=TrialRiskFree";
      return false;
   }
   if(config.AccountStage != ACCOUNT_STAGE_MONITOR_ONLY)
   {
      reason = "StrategyTesterExecutionMode requires AccountStage=MonitorOnly";
      return false;
   }
   if(!IsStrategyTesterResearchSymbolAllowed(config.AllowedSymbols))
   {
      reason = "StrategyTesterExecutionMode requires AllowedSymbols to be one approved research tester symbol: EURUSD, NACUSD.c, or SPCUSD.c";
      return false;
   }
   if(!config.StopLossRequired)
   {
      reason = "StrategyTesterExecutionMode requires StopLossRequired=true";
      return false;
   }
   if(config.MinHoldSeconds < 180)
   {
      reason = "StrategyTesterExecutionMode requires MinHoldSeconds>=180";
      return false;
   }
   if(config.MaxRiskPerTradePct > 0.50)
   {
      reason = "StrategyTesterExecutionMode requires MaxRiskPerTradePct<=0.50";
      return false;
   }
   if(config.RiskPerTradePct > 0.25)
   {
      reason = "StrategyTesterExecutionMode requires RiskPerTradePct<=0.25";
      return false;
   }
   if(config.MaxOpenPositionsTotal != 1 || config.MaxOpenPositionsPerSymbol != 1)
   {
      reason = "StrategyTesterExecutionMode requires MaxOpenPositionsTotal=1 and MaxOpenPositionsPerSymbol=1";
      return false;
   }
   if(config.MaxTradesPerDay <= 0)
   {
      reason = "StrategyTesterExecutionMode requires MaxTradesPerDay>=1";
      return false;
   }
   if(config.MaxServerMessagesPerDay <= 0 || config.MaxServerMessagesPerDay > 2000)
   {
      reason = "StrategyTesterExecutionMode requires MaxServerMessagesPerDay between 1 and 2000";
      return false;
   }
   if(!config.UseSpreadFilter)
   {
      reason = "StrategyTesterExecutionMode requires UseSpreadFilter=true";
      return false;
   }
   if(!config.SpreadUnknownBlocksTrading)
   {
      reason = "StrategyTesterExecutionMode requires SpreadUnknownBlocksTrading=true";
      return false;
   }
   reason = "Strategy Tester simulated execution gates validated";
   return true;
}

bool ValidatePhase5ComplianceConfig(const SUpcomersConfig &config, string &reason)
{
   if(!IsKnownAccountProgram(config.AccountProgram))
   {
      reason = "AccountProgram is unsupported";
      return false;
   }
   if(!IsKnownAccountStage(config.AccountStage))
   {
      reason = "AccountStage is unsupported";
      return false;
   }
   if(!ValidateTrialExecutionConfig(config, reason))
   {
      return false;
   }
   if(config.EnableTrading && !config.EnableTrialExecution &&
      (!config.RequireManualConfirmationText ||
       config.ManualConfirmationText != UPCOMERS_REQUIRED_CONFIRMATION_TEXT))
   {
      reason = "EnableTrading requires exact manual confirmation text";
      return false;
   }
   if(config.EnablePropChallengeMode &&
      !HasRequiredProtectedStageMetadata(config, reason))
   {
      reason = "EnablePropChallengeMode blocked: " + reason;
      return false;
   }
   if(IsRuleUnverifiedAccountProgram(config.AccountProgram) &&
      (config.EnableTrading || config.EnablePropChallengeMode ||
       config.StrategyTesterExecutionMode ||
       IsProtectedAccountStage(config.AccountStage)))
   {
      reason = "AccountProgram rules are unverified; protected or active use is blocked";
      return false;
   }
   if(config.AccountProgram == ACCOUNT_PROGRAM_VANGUARD &&
      (config.EnableTrading || config.EnablePropChallengeMode ||
       config.StrategyTesterExecutionMode ||
       IsProtectedAccountStage(config.AccountStage)) &&
      !HasRequiredProtectedStageMetadata(config, reason))
   {
      reason = "Vanguard blocked until exact rules, trial evidence, audit package, and approval exist: " + reason;
      return false;
   }
   if(IsProtectedAccountStage(config.AccountStage) &&
      !HasRequiredProtectedStageMetadata(config, reason))
   {
      reason = "protected AccountStage blocked: " + reason;
      return false;
   }
   if(config.MaxDailyLossHardPct >= 4.0)
   {
      reason = "MaxDailyLossHardPct must stay below 4 percent";
      return false;
   }
   if(config.MaxOverallLossHardPct >= 7.0)
   {
      reason = "MaxOverallLossHardPct must stay below 7 percent";
      return false;
   }
   if(config.MaxDailyLossSoftPct >= config.MaxDailyLossHardPct)
   {
      reason = "daily soft loss guard must be below hard loss guard";
      return false;
   }
   if(config.MaxOverallLossSoftPct >= config.MaxOverallLossHardPct)
   {
      reason = "overall soft loss guard must be below hard loss guard";
      return false;
   }
   if(config.RiskPerTradePct > config.MaxRiskPerTradePct)
   {
      reason = "RiskPerTradePct exceeds MaxRiskPerTradePct";
      return false;
   }
   if(config.MaxRiskPerTradePct > 0.50)
   {
      reason = "MaxRiskPerTradePct exceeds 0.50 percent";
      return false;
   }
   if(config.MinHoldSeconds < 180)
   {
      reason = "MinHoldSeconds must be at least 180 seconds";
      return false;
   }
   if(!config.StopLossRequired)
   {
      reason = "StopLossRequired must remain true";
      return false;
   }
   if(config.MaxTradesPerDay <= 0 || config.MaxTradesPerDay > 20)
   {
      reason = "MaxTradesPerDay must be between 1 and 20";
      return false;
   }
   if(config.MaxServerMessagesPerDay <= 0 || config.MaxServerMessagesPerDay > 2000)
   {
      reason = "MaxServerMessagesPerDay must be between 1 and 2000";
      return false;
   }
   if(config.MaxOpenPositionsTotal <= 0 || config.MaxOpenPositionsPerSymbol <= 0)
   {
      reason = "position caps must be positive";
      return false;
   }
   if(config.MaxOpenPositionsPerSymbol > config.MaxOpenPositionsTotal)
   {
      reason = "MaxOpenPositionsPerSymbol exceeds MaxOpenPositionsTotal";
      return false;
   }
   if(!HasText(config.AllowedSymbols))
   {
      reason = "AllowedSymbols must not be empty";
      return false;
   }
   if(config.TrialExecutionMagicNumber <= 0)
   {
      reason = "TrialExecutionMagicNumber must be positive";
      return false;
   }
   if(config.AllowGrid || config.AllowMartingale || config.AllowAveragingDown ||
      config.AllowHFT || config.AllowArbitrage || config.AllowCopyTrading ||
      config.AllowScalpingUnder2Minutes)
   {
      reason = "prohibited behavior flags must remain false";
      return false;
   }
   if(config.BrokerTimeMode != BROKER_TIME_MANUAL_UTC_OFFSET)
   {
      reason = "BrokerTimeMode is unsupported; use explicit manual UTC offset";
      return false;
   }
   if(config.BrokerServerUtcOffsetMinutes < -720 || config.BrokerServerUtcOffsetMinutes > 840)
   {
      reason = "BrokerServerUtcOffsetMinutes must be between -720 and 840";
      return false;
   }
   if(config.RequireBrokerTimeValidation && config.AccountStage != ACCOUNT_STAGE_MONITOR_ONLY &&
      !HasText(config.BrokerTimeValidationNote))
   {
      reason = "BrokerTimeValidationNote required before Trial or protected account observation";
      return false;
   }
   if(config.MaxSpreadPoints <= 0)
   {
      reason = "MaxSpreadPoints must be positive";
      return false;
   }
   if(!config.SpreadUnknownBlocksTrading)
   {
      reason = "SpreadUnknownBlocksTrading must remain true";
      return false;
   }
   if(config.EvaluationMode != EVALUATION_ON_NEW_CLOSED_BAR &&
      config.EvaluationMode != EVALUATION_TIMER)
   {
      reason = "EvaluationMode is unsupported";
      return false;
   }
   if(config.MinEvaluationSeconds < 1)
   {
      reason = "MinEvaluationSeconds must be positive";
      return false;
   }
   reason = "Phase 5 compliance config validated";
   return true;
}

bool ValidateRuntimeExecutionConfig(
   const SUpcomersConfig &config,
   const bool isStrategyTesterRuntime,
   string &reason
)
{
   if(!ValidatePhase5ComplianceConfig(config, reason))
      return false;
   if(!ValidateStrategyTesterExecutionConfig(config, isStrategyTesterRuntime, reason))
      return false;
   reason = "runtime execution config validated";
   return true;
}

bool ValidateSafeDefaults(const SUpcomersConfig &config, string &reason)
{
   return ValidatePhase5ComplianceConfig(config, reason);
}

#endif

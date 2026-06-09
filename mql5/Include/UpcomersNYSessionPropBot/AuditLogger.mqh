#ifndef UPCOMERS_NY_SESSION_PROP_BOT_AUDIT_LOGGER_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_AUDIT_LOGGER_MQH

#include "Config.mqh"
#include "Logger.mqh"

class CAuditLogger
{
private:
   CUpcomersLogger *m_logger;

public:
   void Bind(CUpcomersLogger &logger)
   {
      m_logger = &logger;
   }

   void LogStartupSummary(const SUpcomersConfig &config)
   {
      if(m_logger == NULL)
         return;

      m_logger.Info("Audit", "Phase 14 EA startup");
      m_logger.Info("Audit", "Trading, Trial execution, and Strategy Tester execution are disabled by default");
      m_logger.Info(
         "Audit",
         "TradeManager refuses execution unless strict TrialRiskFree-only micro execution gates are active"
      );
      m_logger.Info("Audit", StringFormat("EnableTrading=%s", BoolToText(config.EnableTrading)));
      m_logger.Info(
         "Audit",
         StringFormat("EnableTrialExecution=%s", BoolToText(config.EnableTrialExecution))
      );
      m_logger.Info(
         "Audit",
         StringFormat("StrategyTesterExecutionMode=%s", BoolToText(config.StrategyTesterExecutionMode))
      );
      m_logger.Info(
         "Audit",
         StringFormat("EnablePropChallengeMode=%s", BoolToText(config.EnablePropChallengeMode))
      );
      m_logger.Info(
         "Audit",
         StringFormat("AccountProgram=%s", AccountProgramToString(config.AccountProgram))
      );
      m_logger.Info("Audit", StringFormat("AccountStage=%s", AccountStageToString(config.AccountStage)));
      m_logger.Info("Audit", StringFormat("PropDayResetTimezone=%s", config.PropDayResetTimezone));
      m_logger.Info("Audit", StringFormat("MinHoldSeconds=%d", config.MinHoldSeconds));
      m_logger.Info("Audit", StringFormat("MaxTradesPerDay=%d", config.MaxTradesPerDay));
      m_logger.Info(
         "Audit",
         StringFormat("AllowedSymbols=%s TrialExecutionMagicNumber=%d", config.AllowedSymbols, config.TrialExecutionMagicNumber)
      );
      m_logger.Info(
         "Audit",
         StringFormat("MaxServerMessagesPerDay=%d", config.MaxServerMessagesPerDay)
      );
      m_logger.Info(
         "Audit",
         StringFormat(
            "BrokerTimeMode=%s BrokerServerUtcOffsetMinutes=%d RequireBrokerTimeValidation=%s",
            BrokerTimeModeToString(config.BrokerTimeMode),
            config.BrokerServerUtcOffsetMinutes,
            BoolToText(config.RequireBrokerTimeValidation)
         )
      );
      m_logger.Info(
         "Audit",
         StringFormat(
            "UseSpreadFilter=%s MaxSpreadPoints=%d SpreadUnknownBlocksTrading=%s",
            BoolToText(config.UseSpreadFilter),
            config.MaxSpreadPoints,
            BoolToText(config.SpreadUnknownBlocksTrading)
         )
      );
      m_logger.Info(
         "Audit",
         StringFormat(
            "EvaluationMode=%s MinEvaluationSeconds=%d LogThrottleSkips=%s",
            EvaluationModeToString(config.EvaluationMode),
            config.MinEvaluationSeconds,
            BoolToText(config.LogThrottleSkips)
         )
      );
      m_logger.Info(
         "Audit",
         StringFormat(
            "daily loss guard soft/hard %.2f/%.2f",
            config.MaxDailyLossSoftPct,
            config.MaxDailyLossHardPct
         )
      );
      m_logger.Info(
         "Audit",
         StringFormat(
            "overall loss guard soft/hard %.2f/%.2f",
            config.MaxOverallLossSoftPct,
            config.MaxOverallLossHardPct
         )
      );
      m_logger.Warn(
         "Audit",
         "Trial Risk-Free testing is not approval for Surge 2 Step, Vanguard, or funded trading"
      );
      m_logger.Warn("Audit", "Surge 2 Step rules are unverified and not encoded");
      m_logger.Warn("Audit", "Vanguard remains protected until exact rules and approval metadata exist");
   }

   void LogValidationResult(const bool isValid, const string reason)
   {
      if(m_logger == NULL)
         return;
      if(isValid)
         m_logger.Info("Audit", "startup validation PASS: " + reason);
      else
         m_logger.Error("Audit", "startup validation FAIL: " + reason);
   }

   void LogUnresolvedRuleWarnings(const SUpcomersConfig &config)
   {
      if(m_logger == NULL)
         return;
      if(!HasText(config.PropDayResetTimezoneConfirmationId))
      {
         m_logger.Warn(
            "Audit",
            "TODO: confirm current Upcomers daily loss reset timezone before challenge use"
         );
      }
      if(!HasText(config.DynamicRiskShieldConfirmationId))
      {
         m_logger.Warn(
            "Audit",
            "TODO: verify exact Dynamic Risk Shield calculation before challenge presets"
         );
      }
      if(config.RequireBrokerTimeValidation && !HasText(config.BrokerTimeValidationNote))
      {
         m_logger.Warn(
            "Audit",
            "Broker server UTC offset and New York session mapping must be validated before Trial observation"
         );
      }
      if(config.AccountProgram == ACCOUNT_PROGRAM_SURGE_2_STEP)
      {
         m_logger.Warn(
            "Audit",
            "TODO: review and encode exact Surge 2 Step rules before any challenge use"
         );
      }
      if(config.AccountProgram == ACCOUNT_PROGRAM_VANGUARD)
      {
         m_logger.Warn(
            "Audit",
            "TODO: confirm Vanguard-specific rules before any Vanguard use"
         );
      }
      if(IsProtectedAccountStage(config.AccountStage) || config.EnablePropChallengeMode ||
         IsProtectedAccountProgram(config.AccountProgram))
      {
         m_logger.Warn(
            "Audit",
            "Protected account programs remain blocked without rules review and approval metadata"
         );
      }
   }

   void LogDecision(const string component, const string decision)
   {
      if(m_logger != NULL)
         m_logger.Info(component, decision);
   }
};

#endif

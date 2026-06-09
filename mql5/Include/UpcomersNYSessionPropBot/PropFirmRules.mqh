#ifndef UPCOMERS_NY_SESSION_PROP_BOT_PROP_FIRM_RULES_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_PROP_FIRM_RULES_MQH

#include "Config.mqh"

class CPropFirmRules
{
public:
   int BuildPropDayKey(const datetime eventTime, const string propDayResetTimezone)
   {
      if(StringLen(propDayResetTimezone) == 0)
         return 0;
      MqlDateTime propTime;
      TimeToStruct(eventTime, propTime);
      return propTime.year * 10000 + propTime.mon * 100 + propTime.day;
   }

   ENUM_UPCOMERS_GUARD_STATUS CheckDailyLossGuard(
      const SUpcomersConfig &config,
      const double observedDailyLossPct,
      string &reason
   )
   {
      if(!HasText(config.PropDayResetTimezoneConfirmationId))
      {
         reason = StringFormat(
            "UNKNOWN_RULE_BLOCK: PropDayResetTimezone=%s is configurable but current Upcomers reset timezone is unconfirmed",
            config.PropDayResetTimezone
         );
         return GUARD_STATUS_UNKNOWN_RULE_BLOCK;
      }
      if(observedDailyLossPct >= config.MaxDailyLossHardPct)
      {
         reason = "HARD_STOP: daily loss hard guard reached";
         return GUARD_STATUS_HARD_STOP;
      }
      if(observedDailyLossPct >= config.MaxDailyLossSoftPct)
      {
         reason = "SOFT_STOP: daily loss soft guard reached";
         return GUARD_STATUS_SOFT_STOP;
      }
      reason = "OK: daily loss guard below configured limits";
      return GUARD_STATUS_OK;
   }

   ENUM_UPCOMERS_GUARD_STATUS CheckOverallLossGuard(
      const SUpcomersConfig &config,
      const double observedOverallLossPct,
      string &reason
   )
   {
      if(!HasText(config.DynamicRiskShieldConfirmationId))
      {
         reason = "UNKNOWN_RULE_BLOCK: exact Dynamic Risk Shield calculation must be verified before challenge presets";
         return GUARD_STATUS_UNKNOWN_RULE_BLOCK;
      }
      if(observedOverallLossPct >= config.MaxOverallLossHardPct)
      {
         reason = "HARD_STOP: overall loss hard guard reached";
         return GUARD_STATUS_HARD_STOP;
      }
      if(observedOverallLossPct >= config.MaxOverallLossSoftPct)
      {
         reason = "SOFT_STOP: overall loss soft guard reached";
         return GUARD_STATUS_SOFT_STOP;
      }
      reason = "OK: overall loss guard below configured limits";
      return GUARD_STATUS_OK;
   }

   bool CheckRules(const SUpcomersConfig &config, string &reason)
   {
      string metadataReason = "";
      if(config.AccountProgram == ACCOUNT_PROGRAM_SURGE_2_STEP)
      {
         reason = "Surge 2 Step is rule-unverified and blocked from challenge use";
         return true;
      }
      if(config.AccountProgram == ACCOUNT_PROGRAM_VANGUARD)
      {
         reason = "Vanguard is protected until exact rules, trial evidence, audit package, and human approval exist";
         return true;
      }
      if(IsProtectedAccountStage(config.AccountStage) &&
         !HasRequiredProtectedStageMetadata(config, metadataReason))
      {
         reason = "protected account stage is blocked until audit and human approval: " + metadataReason;
         return false;
      }
      if(config.EnablePropChallengeMode &&
         !HasRequiredProtectedStageMetadata(config, metadataReason))
      {
         reason = "prop challenge mode is blocked until audit and human approval: " + metadataReason;
         return false;
      }
      if(config.AccountStage == ACCOUNT_STAGE_TRIAL)
      {
         reason = "Trial Risk-Free testing is not approval for Surge 2 Step, Vanguard, or funded trading";
         return true;
      }
      reason = "prop-firm rule guard is monitor-only in Phase 5";
      return true;
   }
};

#endif

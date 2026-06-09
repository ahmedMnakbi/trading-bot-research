#ifndef UPCOMERS_NY_SESSION_PROP_BOT_STRATEGY_DIAGNOSTICS_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_STRATEGY_DIAGNOSTICS_MQH

#include "Config.mqh"
#include "StrategyBase.mqh"

class CStrategyDiagnostics
{
private:
   int m_totalEvaluations;
   int m_waitSignals;
   int m_setupFormingSignals;
   int m_skipSessionSignals;
   int m_spreadBlockReasons;
   int m_orbWidthBlockReasons;
   int m_retestFailReasons;
   int m_orbSignalCooldownReasons;
   int m_enterLongSignals;
   int m_enterShortSignals;
   int m_vwapBiasLongReasons;
   int m_vwapBiasShortReasons;
   int m_vwapFlatBlockReasons;
   int m_impulseMissingReasons;
   int m_pullbackNearVwapReasons;
   int m_rejectionCloseOkReasons;
   int m_testerOrderAttempts;

   bool HasToken(const SStrategyDecision &decision, const string token) const
   {
      return StringFind(decision.ReasonCode, token) >= 0 ||
             StringFind(decision.ReasonCodes, token) >= 0 ||
             StringFind(decision.Reason, token) >= 0 ||
             SignalToString(decision.Signal) == token;
   }

   void AppendCount(string &summary, const string name, const int value) const
   {
      if(StringLen(summary) > 0)
         summary += "|";
      summary += StringFormat("%s:%d", name, value);
   }

public:
   void Reset()
   {
      m_totalEvaluations = 0;
      m_waitSignals = 0;
      m_setupFormingSignals = 0;
      m_skipSessionSignals = 0;
      m_spreadBlockReasons = 0;
      m_orbWidthBlockReasons = 0;
      m_retestFailReasons = 0;
      m_orbSignalCooldownReasons = 0;
      m_enterLongSignals = 0;
      m_enterShortSignals = 0;
      m_vwapBiasLongReasons = 0;
      m_vwapBiasShortReasons = 0;
      m_vwapFlatBlockReasons = 0;
      m_impulseMissingReasons = 0;
      m_pullbackNearVwapReasons = 0;
      m_rejectionCloseOkReasons = 0;
      m_testerOrderAttempts = 0;
   }

   void RecordDecision(const SStrategyDecision &decision)
   {
      m_totalEvaluations++;

      if(decision.Signal == SIGNAL_WAIT)
         m_waitSignals++;
      else if(decision.Signal == SIGNAL_SETUP_FORMING)
         m_setupFormingSignals++;
      else if(decision.Signal == SIGNAL_SKIP_SESSION)
         m_skipSessionSignals++;
      else if(decision.Signal == SIGNAL_ENTER_LONG_INTENT)
         m_enterLongSignals++;
      else if(decision.Signal == SIGNAL_ENTER_SHORT_INTENT)
         m_enterShortSignals++;

      if(decision.Signal == SIGNAL_SKIP_SPREAD || HasToken(decision, "SPREAD_BLOCK"))
         m_spreadBlockReasons++;
      if(HasToken(decision, "ORB_WIDTH_BLOCK"))
         m_orbWidthBlockReasons++;
      if(HasToken(decision, "RETEST_FAIL"))
         m_retestFailReasons++;
      if(HasToken(decision, "ORB_SIGNAL_COOLDOWN"))
         m_orbSignalCooldownReasons++;
      if(HasToken(decision, "VWAP_BIAS_LONG"))
         m_vwapBiasLongReasons++;
      if(HasToken(decision, "VWAP_BIAS_SHORT"))
         m_vwapBiasShortReasons++;
      if(HasToken(decision, "VWAP_FLAT_BLOCK"))
         m_vwapFlatBlockReasons++;
      if(HasToken(decision, "IMPULSE_MISSING"))
         m_impulseMissingReasons++;
      if(HasToken(decision, "PULLBACK_NEAR_VWAP"))
         m_pullbackNearVwapReasons++;
      if(HasToken(decision, "REJECTION_CLOSE_OK"))
         m_rejectionCloseOkReasons++;
   }

   void RecordTesterOrderAttempt()
   {
      m_testerOrderAttempts++;
   }

   int TotalEvaluations() const
   {
      return m_totalEvaluations;
   }

   string ReasonCodeSummary() const
   {
      string summary = "";
      AppendCount(summary, "WAIT", m_waitSignals);
      AppendCount(summary, "SETUP_FORMING", m_setupFormingSignals);
      AppendCount(summary, "SKIP_SESSION", m_skipSessionSignals);
      AppendCount(summary, "SPREAD_BLOCK", m_spreadBlockReasons);
      AppendCount(summary, "ORB_WIDTH_BLOCK", m_orbWidthBlockReasons);
      AppendCount(summary, "RETEST_FAIL", m_retestFailReasons);
      AppendCount(summary, "ORB_SIGNAL_COOLDOWN", m_orbSignalCooldownReasons);
      AppendCount(summary, "ENTER_LONG_INTENT", m_enterLongSignals);
      AppendCount(summary, "ENTER_SHORT_INTENT", m_enterShortSignals);
      AppendCount(summary, "VWAP_BIAS_LONG", m_vwapBiasLongReasons);
      AppendCount(summary, "VWAP_BIAS_SHORT", m_vwapBiasShortReasons);
      AppendCount(summary, "VWAP_FLAT_BLOCK", m_vwapFlatBlockReasons);
      AppendCount(summary, "IMPULSE_MISSING", m_impulseMissingReasons);
      AppendCount(summary, "PULLBACK_NEAR_VWAP", m_pullbackNearVwapReasons);
      AppendCount(summary, "REJECTION_CLOSE_OK", m_rejectionCloseOkReasons);
      return summary;
   }

   string Summary(
      const string strategy,
      const bool testerExecutionMode,
      const bool testerRuntime,
      const string eventName
   ) const
   {
      return StringFormat(
         "STRATEGY_DIAGNOSTICS_SUMMARY strategy=%s total_evaluations=%d enter_long=%d enter_short=%d tester_execution_mode=%s tester_runtime=%s tester_orders_attempted=%d top_reason_codes=%s event=%s",
         strategy,
         m_totalEvaluations,
         m_enterLongSignals,
         m_enterShortSignals,
         BoolToText(testerExecutionMode),
         BoolToText(testerRuntime),
         m_testerOrderAttempts,
         ReasonCodeSummary(),
         eventName
      );
   }
};

#endif

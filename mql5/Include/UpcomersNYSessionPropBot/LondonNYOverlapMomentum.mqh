#ifndef UPCOMERS_NY_SESSION_PROP_BOT_LONDON_NY_OVERLAP_MOMENTUM_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_LONDON_NY_OVERLAP_MOMENTUM_MQH

#include "StrategyBase.mqh"
#include "SessionManager.mqh"

class CLondonNYOverlapMomentumStrategy
{
private:
   int m_lastSignalSessionKey;
   int m_signalsThisSession;
   string m_lastSetupFingerprint;

   bool DuplicateSetupBlocked(const string fingerprint)
   {
      if(m_lastSetupFingerprint == fingerprint)
         return true;
      m_lastSetupFingerprint = fingerprint;
      return false;
   }

   double AverageRange(const MqlRates &rates[], const int start, const int count)
   {
      double total = 0.0;
      int used = 0;
      for(int i = start; i < start + count; i++)
      {
         total += MathAbs(rates[i].high - rates[i].low);
         used++;
      }
      if(used <= 0)
         return 0.0;
      return total / used;
   }

public:
   CLondonNYOverlapMomentumStrategy()
   {
      m_lastSignalSessionKey = 0;
      m_signalsThisSession = 0;
      m_lastSetupFingerprint = "";
   }

   void Evaluate(
      const string symbol,
      const ENUM_TIMEFRAMES timeframe,
      const datetime now,
      CSessionManager &sessionManager,
      SStrategyDecision &decision,
      const int maxSignalsPerSession = 1,
      const int minHoldSeconds = 180
   )
   {
      const string strategyName = "LondonNYOverlapMomentum";
      const ENUM_TIMEFRAMES analysisTimeframe = PERIOD_M5;
      datetime newYorkTime = 0;
      string newYorkReason = "";
      bool hasNewYorkTime = sessionManager.TryConvertBrokerServerToNewYork(
         now,
         newYorkTime,
         newYorkReason
      );
      string symbolClass = sessionManager.SymbolClassFor(symbol);
      string sessionTag = "LONDON_NY_OVERLAP_0800_1200_AMERICA_NEW_YORK";

      if(sessionManager.IsIndexSymbol(symbol))
      {
         SetSkipDecision(
            decision,
            SIGNAL_SKIP_SESSION,
            strategyName,
            symbol,
            analysisTimeframe,
            "OVERLAP_INDEX_DEFAULT_BLOCK",
            "London/New York overlap momentum is FX/gold-focused by default; index CFDs require explicit later approval",
            now
         );
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            "TICK_VOLUME_USED"
         );
         return;
      }

      string sessionReason = "";
      if(!sessionManager.IsLondonNewYorkOverlap(now, symbol, sessionReason))
      {
         SetSkipDecision(
            decision,
            SIGNAL_SKIP_SESSION,
            strategyName,
            symbol,
            analysisTimeframe,
            "SKIP_SESSION",
            sessionReason,
            now
         );
         AppendReasonCode(decision, "LATE_OVERLAP_BLOCK");
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            "TICK_VOLUME_USED"
         );
         return;
      }

      int sessionKey = sessionManager.StrategySessionKey(now);
      if(m_lastSignalSessionKey != sessionKey)
      {
         m_lastSignalSessionKey = sessionKey;
         m_signalsThisSession = 0;
         m_lastSetupFingerprint = "";
      }
      if(m_signalsThisSession >= maxSignalsPerSession)
      {
         SetWaitDecision(decision, "OVERLAP_SIGNAL_CAP: per-session signal cap reached");
         PopulateStrategyDecision(decision, strategyName, symbol, analysisTimeframe, "OVERLAP_SIGNAL_CAP", now);
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            "TICK_VOLUME_USED"
         );
         return;
      }

      MqlRates rates[];
      ArraySetAsSeries(rates, true);
      const int referenceRangeBars = 12; // 07:00-08:00 New York on closed M5 bars.
      const int retestWindowBars = 3;
      int barsNeeded = referenceRangeBars + retestWindowBars + 5;
      int bars = CopyRates(symbol, analysisTimeframe, UPCOMERS_CLOSED_BAR_SHIFT, barsNeeded, rates);
      if(bars < barsNeeded)
      {
         SetSkipDecision(
            decision,
            SIGNAL_SKIP_DATA,
            strategyName,
            symbol,
            analysisTimeframe,
            "SKIP_DATA_OVERLAP_BARS",
            "reference range 07:00-08:00 New York needs closed M5 bars",
            now
         );
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            "TICK_VOLUME_USED"
         );
         return;
      }

      double referenceHigh = rates[retestWindowBars + 1].high;
      double referenceLow = rates[retestWindowBars + 1].low;
      for(int i = retestWindowBars + 1; i < retestWindowBars + 1 + referenceRangeBars; i++)
      {
         if(rates[i].high > referenceHigh)
            referenceHigh = rates[i].high;
         if(rates[i].low < referenceLow)
            referenceLow = rates[i].low;
      }

      double atr = AverageRange(rates, 0, 14);
      if(atr <= 0.0)
      {
         SetSkipDecision(
            decision,
            SIGNAL_SKIP_DATA,
            strategyName,
            symbol,
            analysisTimeframe,
            "SKIP_DATA_OVERLAP_ATR",
            "overlap trend alignment needs positive closed-bar range",
            now
         );
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            "TICK_VOLUME_USED"
         );
         return;
      }

      bool trendLong = rates[0].close > rates[3].close;
      bool trendShort = rates[0].close < rates[3].close;
      bool breakUp = rates[1].close > referenceHigh;
      bool breakDown = rates[1].close < referenceLow;
      bool retestLong = rates[0].low <= referenceHigh && rates[0].close > referenceHigh;
      bool retestShort = rates[0].high >= referenceLow && rates[0].close < referenceLow;
      string fingerprint = StringFormat("%s:%d:%.5f:%.5f", symbol, sessionKey, referenceHigh, referenceLow);
      if(DuplicateSetupBlocked(fingerprint))
      {
         SetWaitDecision(decision, "OVERLAP_SIGNAL_COOLDOWN: repeated setup fingerprint suppressed");
         PopulateStrategyDecision(decision, strategyName, symbol, analysisTimeframe, "OVERLAP_SIGNAL_COOLDOWN", now);
         AppendReasonCode(decision, "OVERLAP_WINDOW_OK");
         AppendReasonCode(decision, "REFERENCE_RANGE_BUILT");
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            "TICK_VOLUME_USED"
         );
         return;
      }

      if(breakUp && trendLong && retestLong)
      {
         double stopLoss = MathMin(rates[0].low, referenceLow);
         double takeProfit = rates[0].close + ((rates[0].close - stopLoss) * 1.5);
         SetEntryIntentDecision(
            decision,
            SIGNAL_ENTER_LONG_INTENT,
            strategyName,
            symbol,
            analysisTimeframe,
            "RANGE_BREAK_UP",
            "monitor-only long intent: overlap reference range break/retest with trend alignment",
            now,
            stopLoss,
            takeProfit,
            0.75
         );
         SetSuggestedEntry(decision, rates[0].close);
         AppendReasonCode(decision, "OVERLAP_WINDOW_OK");
         AppendReasonCode(decision, "REFERENCE_RANGE_BUILT");
         AppendReasonCode(decision, "TREND_ALIGN_OK");
         AppendReasonCode(decision, "RETEST_PASS");
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            "TICK_VOLUME_USED"
         );
         m_signalsThisSession++;
         return;
      }

      if(breakDown && trendShort && retestShort)
      {
         double stopLoss = MathMax(rates[0].high, referenceHigh);
         double takeProfit = rates[0].close - ((stopLoss - rates[0].close) * 1.5);
         SetEntryIntentDecision(
            decision,
            SIGNAL_ENTER_SHORT_INTENT,
            strategyName,
            symbol,
            analysisTimeframe,
            "RANGE_BREAK_DOWN",
            "monitor-only short intent: overlap reference range break/retest with trend alignment",
            now,
            stopLoss,
            takeProfit,
            0.75
         );
         SetSuggestedEntry(decision, rates[0].close);
         AppendReasonCode(decision, "OVERLAP_WINDOW_OK");
         AppendReasonCode(decision, "REFERENCE_RANGE_BUILT");
         AppendReasonCode(decision, "TREND_ALIGN_OK");
         AppendReasonCode(decision, "RETEST_PASS");
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            "TICK_VOLUME_USED"
         );
         m_signalsThisSession++;
         return;
      }

      SetSetupFormingDecision(
         decision,
         strategyName,
         symbol,
         analysisTimeframe,
         "REFERENCE_RANGE_BUILT",
         "overlap monitor-only break/retest setup is forming; no entry intent without trend alignment",
         now,
         0.0
      );
      AppendReasonCode(decision, "OVERLAP_WINDOW_OK");
      if(breakUp)
         AppendReasonCode(decision, "RANGE_BREAK_UP");
      if(breakDown)
         AppendReasonCode(decision, "RANGE_BREAK_DOWN");
      if(trendLong || trendShort)
         AppendReasonCode(decision, "TREND_ALIGN_OK");
      if(retestLong || retestShort)
         AppendReasonCode(decision, "RETEST_PASS");
      AppendReasonCode(decision, "NEWS_BLOCK");
      SetDecisionContext(
         decision,
         symbolClass,
         sessionTag,
         newYorkTime,
         hasNewYorkTime,
         minHoldSeconds,
         "SPREAD_CHECKED_UPSTREAM",
         "TICK_VOLUME_USED"
      );
   }
};

#endif

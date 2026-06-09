#ifndef UPCOMERS_NY_SESSION_PROP_BOT_VOLATILITY_EXPANSION_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_VOLATILITY_EXPANSION_MQH

#include "StrategyBase.mqh"
#include "SessionManager.mqh"

class CVolatilityExpansionStrategy
{
private:
   // VolumeTypeUsed is populated through SetDecisionContext for every decision.
   int m_lastSignalSessionKey;
   int m_signalsThisSession;
   string m_lastSetupFingerprint;

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

   double BarVolume(const MqlRates &bar, string &volumeType)
   {
      if(bar.real_volume > 0)
      {
         volumeType = "REAL_VOLUME_USED";
         return (double)bar.real_volume;
      }
      volumeType = "TICK_VOLUME_USED";
      return (double)bar.tick_volume;
   }

   double MedianVolume(const MqlRates &rates[], const int start, const int count, string &volumeType)
   {
      double volumes[];
      ArrayResize(volumes, count);
      for(int i = 0; i < count; i++)
      {
         string localVolumeType = "";
         volumes[i] = BarVolume(rates[start + i], localVolumeType);
         if(volumeType != "REAL_VOLUME_USED")
            volumeType = localVolumeType;
      }
      ArraySort(volumes);
      return volumes[count / 2];
   }

   bool DuplicateSetupBlocked(const string fingerprint)
   {
      if(m_lastSetupFingerprint == fingerprint)
         return true;
      m_lastSetupFingerprint = fingerprint;
      return false;
   }

public:
   CVolatilityExpansionStrategy()
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
      const string strategyName = "VolatilityExpansion";
      const ENUM_TIMEFRAMES analysisTimeframe = PERIOD_M5;
      const int setupBoxBars = 12;
      const double contractionAtrMultiple = 1.25;
      const double rangeExpansionAtrMultiple = 1.25;
      const double volumeExpansionMultiple = 1.30;
      datetime newYorkTime = 0;
      string newYorkReason = "";
      bool hasNewYorkTime = sessionManager.TryConvertBrokerServerToNewYork(
         now,
         newYorkTime,
         newYorkReason
      );
      string symbolClass = sessionManager.SymbolClassFor(symbol);
      string sessionTag = sessionManager.SessionTagForSymbol(symbol);

      string sessionReason = "";
      if(!sessionManager.IsEntrySessionForSymbol(now, symbol, sessionReason))
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
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            "VOLUME_PENDING"
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
         SetWaitDecision(decision, "VOLATILITY_EXPANSION_SIGNAL_CAP: per-session signal cap reached");
         PopulateStrategyDecision(
            decision,
            strategyName,
            symbol,
            analysisTimeframe,
            "VOLATILITY_EXPANSION_SIGNAL_CAP",
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
            "VOLUME_PENDING"
         );
         return;
      }

      MqlRates rates[];
      ArraySetAsSeries(rates, true);
      int barsNeeded = setupBoxBars + 20;
      int bars = CopyRates(symbol, analysisTimeframe, UPCOMERS_CLOSED_BAR_SHIFT, barsNeeded, rates);
      if(bars < barsNeeded)
      {
         SetSkipDecision(
            decision,
            SIGNAL_SKIP_DATA,
            strategyName,
            symbol,
            analysisTimeframe,
            "SKIP_DATA_EXPANSION_BARS",
            "volume/volatility expansion needs closed M5 setup box bars",
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
            "VOLUME_PENDING"
         );
         return;
      }

      double setupHigh = rates[1].high;
      double setupLow = rates[1].low;
      for(int i = 1; i <= setupBoxBars; i++)
      {
         if(rates[i].high > setupHigh)
            setupHigh = rates[i].high;
         if(rates[i].low < setupLow)
            setupLow = rates[i].low;
      }

      double atr = AverageRange(rates, 1, 14);
      if(atr <= 0.0)
      {
         SetSkipDecision(
            decision,
            SIGNAL_SKIP_DATA,
            strategyName,
            symbol,
            analysisTimeframe,
            "SKIP_DATA_EXPANSION_ATR",
            "expansion trigger needs positive ATR from closed bars",
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
            "VOLUME_PENDING"
         );
         return;
      }

      string volumeType = "";
      double medianVolume = MedianVolume(rates, 1, setupBoxBars, volumeType);
      string triggerVolumeType = "";
      double triggerVolume = BarVolume(rates[0], triggerVolumeType);
      if(triggerVolumeType == "REAL_VOLUME_USED")
         volumeType = "REAL_VOLUME_USED";
      else if(volumeType != "REAL_VOLUME_USED")
         volumeType = "TICK_VOLUME_USED";

      bool contractionOk = (setupHigh - setupLow) <= atr * contractionAtrMultiple;
      bool rangeExpandOk = MathAbs(rates[0].high - rates[0].low) >= atr * rangeExpansionAtrMultiple;
      bool volumeExpandOk = medianVolume > 0.0 && triggerVolume >= medianVolume * volumeExpansionMultiple;
      bool breakUp = rates[0].close > setupHigh;
      bool breakDown = rates[0].close < setupLow;
      string fingerprint = StringFormat("%s:%d:%.5f:%.5f", symbol, sessionKey, setupHigh, setupLow);

      if(DuplicateSetupBlocked(fingerprint))
      {
         SetWaitDecision(decision, "VOLATILITY_EXPANSION_SIGNAL_COOLDOWN: repeated setup fingerprint suppressed");
         PopulateStrategyDecision(
            decision,
            strategyName,
            symbol,
            analysisTimeframe,
            "VOLATILITY_EXPANSION_SIGNAL_COOLDOWN",
            now
         );
         AppendReasonCode(decision, "SETUP_BOX_BUILT");
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            volumeType
         );
         return;
      }

      if(contractionOk && rangeExpandOk && volumeExpandOk && breakUp)
      {
         double stopLoss = MathMin(setupLow, rates[0].low - (atr * 0.10));
         double takeProfit = rates[0].close + ((rates[0].close - stopLoss) * 1.5);
         SetEntryIntentDecision(
            decision,
            SIGNAL_ENTER_LONG_INTENT,
            strategyName,
            symbol,
            analysisTimeframe,
            "BREAK_UP",
            "monitor-only long intent: setup box contraction, range expansion, and volume expansion confirmed",
            now,
            stopLoss,
            takeProfit,
            0.75
         );
         SetSuggestedEntry(decision, rates[0].close);
         AppendReasonCode(decision, "SETUP_BOX_BUILT");
         AppendReasonCode(decision, "CONTRACTION_OK");
         AppendReasonCode(decision, "RANGE_EXPAND_OK");
         AppendReasonCode(decision, "VOLUME_EXPAND_OK");
         AppendReasonCode(decision, volumeType);
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            volumeType
         );
         m_signalsThisSession++;
         return;
      }

      if(contractionOk && rangeExpandOk && volumeExpandOk && breakDown)
      {
         double stopLoss = MathMax(setupHigh, rates[0].high + (atr * 0.10));
         double takeProfit = rates[0].close - ((stopLoss - rates[0].close) * 1.5);
         SetEntryIntentDecision(
            decision,
            SIGNAL_ENTER_SHORT_INTENT,
            strategyName,
            symbol,
            analysisTimeframe,
            "BREAK_DOWN",
            "monitor-only short intent: setup box contraction, range expansion, and volume expansion confirmed",
            now,
            stopLoss,
            takeProfit,
            0.75
         );
         SetSuggestedEntry(decision, rates[0].close);
         AppendReasonCode(decision, "SETUP_BOX_BUILT");
         AppendReasonCode(decision, "CONTRACTION_OK");
         AppendReasonCode(decision, "RANGE_EXPAND_OK");
         AppendReasonCode(decision, "VOLUME_EXPAND_OK");
         AppendReasonCode(decision, volumeType);
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            volumeType
         );
         m_signalsThisSession++;
         return;
      }

      SetSetupFormingDecision(
         decision,
         strategyName,
         symbol,
         analysisTimeframe,
         "SETUP_BOX_BUILT",
         "monitor-only setup box built; waiting for contraction, expansion, and volume confirmation",
         now,
         0.0
      );
      if(contractionOk)
         AppendReasonCode(decision, "CONTRACTION_OK");
      if(rangeExpandOk)
         AppendReasonCode(decision, "RANGE_EXPAND_OK");
      if(volumeExpandOk)
         AppendReasonCode(decision, "VOLUME_EXPAND_OK");
      if(breakUp)
         AppendReasonCode(decision, "BREAK_UP");
      if(breakDown)
         AppendReasonCode(decision, "BREAK_DOWN");
      AppendReasonCode(decision, volumeType);
      AppendReasonCode(decision, "EXHAUSTION_BLOCK");
      SetDecisionContext(
         decision,
         symbolClass,
         sessionTag,
         newYorkTime,
         hasNewYorkTime,
         minHoldSeconds,
         "SPREAD_CHECKED_UPSTREAM",
         volumeType
      );
   }
};

#endif

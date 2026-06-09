#ifndef UPCOMERS_NY_SESSION_PROP_BOT_NOISE_BAND_MOMENTUM_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_NOISE_BAND_MOMENTUM_MQH

#include "StrategyBase.mqh"
#include "SessionManager.mqh"

class CNoiseBandMomentumStrategy
{
private:
   int m_lastSignalSessionKey;
   int m_signalsThisSession;
   string m_lastSetupFingerprint;

   double ClosedBarTypicalPrice(const MqlRates &bar)
   {
      return (bar.high + bar.low + bar.close) / 3.0;
   }

   double CalculateVwap(const MqlRates &rates[], const int count)
   {
      double weightedPriceVolume = 0.0;
      double totalVolume = 0.0;
      for(int i = 0; i < count; i++)
      {
         double volume = (double)rates[i].tick_volume;
         if(volume <= 0.0)
            continue;
         weightedPriceVolume += ClosedBarTypicalPrice(rates[i]) * volume;
         totalVolume += volume;
      }
      if(totalVolume <= 0.0)
         return 0.0;
      return weightedPriceVolume / totalVolume;
   }

   double CalculateAtr(const MqlRates &rates[], const int count)
   {
      double total = 0.0;
      int used = 0;
      for(int i = 0; i < count; i++)
      {
         total += MathAbs(rates[i].high - rates[i].low);
         used++;
      }
      if(used <= 0)
         return 0.0;
      return total / used;
   }

   double CalculateStdDevFromVwap(const MqlRates &rates[], const int count, const double vwap)
   {
      double sum = 0.0;
      int used = 0;
      for(int i = 0; i < count; i++)
      {
         double distance = rates[i].close - vwap;
         sum += distance * distance;
         used++;
      }
      if(used <= 1)
         return 0.0;
      return MathSqrt(sum / used);
   }

   bool DuplicateSetupBlocked(const string fingerprint)
   {
      if(m_lastSetupFingerprint == fingerprint)
         return true;
      m_lastSetupFingerprint = fingerprint;
      return false;
   }

public:
   CNoiseBandMomentumStrategy()
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
      const string strategyName = "NoiseBandMomentum";
      const ENUM_TIMEFRAMES analysisTimeframe = PERIOD_M5;
      const double atrBandMultiplier = 1.20;
      const double stdDevBandMultiplier = 1.50;
      const double normalizedMomentumThreshold = 0.50;
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
         SetWaitDecision(decision, "NOISE_BAND_SIGNAL_CAP: per-session signal cap reached");
         PopulateStrategyDecision(decision, strategyName, symbol, analysisTimeframe, "NOISE_BAND_SIGNAL_CAP", now);
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
      int barsNeeded = 40;
      int bars = CopyRates(symbol, analysisTimeframe, UPCOMERS_CLOSED_BAR_SHIFT, barsNeeded, rates);
      if(bars < barsNeeded)
      {
         SetSkipDecision(
            decision,
            SIGNAL_SKIP_DATA,
            strategyName,
            symbol,
            analysisTimeframe,
            "SKIP_DATA_NOISE_BAND_BARS",
            "dynamic noise-band momentum needs closed M5 lookback bars",
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

      double vwap = CalculateVwap(rates, bars);
      double atr = CalculateAtr(rates, 14);
      double stdDev = CalculateStdDevFromVwap(rates, 20, vwap);
      if(vwap <= 0.0 || atr <= 0.0 || stdDev <= 0.0)
      {
         SetSkipDecision(
            decision,
            SIGNAL_SKIP_DATA,
            strategyName,
            symbol,
            analysisTimeframe,
            "SKIP_DATA_NOISE_BAND_INPUTS",
            "derived noise-band rule needs VWAP, ATR, and StdDev from closed bars",
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

      double bandWidth = MathMax(atr * atrBandMultiplier, stdDev * stdDevBandMultiplier);
      double previousBandWidth = MathMax(
         CalculateAtr(rates, 28) * atrBandMultiplier,
         CalculateStdDevFromVwap(rates, 35, vwap) * stdDevBandMultiplier
      );
      bool bandCompressed = bandWidth <= previousBandWidth * 0.85;
      if(!bandCompressed)
      {
         SetSetupFormingDecision(
            decision,
            strategyName,
            symbol,
            analysisTimeframe,
            "BAND_COMPRESSED",
            "BAND_COMPRESSED not yet true for derived monitor-only noise-band rule",
            now,
            0.0
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

      double upperBand = vwap + bandWidth;
      double lowerBand = vwap - bandWidth;
      double normalizedMomentum = MathAbs(rates[0].close - rates[2].close) / atr;
      bool expansionOk = MathAbs(rates[0].high - rates[0].low) >= atr * 1.10;
      bool momentumOk = normalizedMomentum >= normalizedMomentumThreshold;
      string fingerprint = StringFormat("%s:%d:%.5f:%.5f", symbol, sessionKey, upperBand, lowerBand);
      if(DuplicateSetupBlocked(fingerprint))
      {
         SetWaitDecision(decision, "NOISE_BAND_SIGNAL_COOLDOWN: repeated setup fingerprint suppressed");
         PopulateStrategyDecision(decision, strategyName, symbol, analysisTimeframe, "NOISE_BAND_SIGNAL_COOLDOWN", now);
         AppendReasonCode(decision, "BAND_COMPRESSED");
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

      if(rates[0].close > upperBand && expansionOk && momentumOk)
      {
         double stopLoss = MathMin(rates[0].low, vwap - (atr * 0.25));
         double takeProfit = rates[0].close + ((rates[0].close - stopLoss) * 1.5);
         SetEntryIntentDecision(
            decision,
            SIGNAL_ENTER_LONG_INTENT,
            strategyName,
            symbol,
            analysisTimeframe,
            "BAND_BREAK_UP",
            "monitor-only long intent: derived noise-band break plus expansion and normalized momentum",
            now,
            stopLoss,
            takeProfit,
            MathMin(1.0, normalizedMomentum)
         );
         SetSuggestedEntry(decision, rates[0].close);
         AppendReasonCode(decision, "BAND_COMPRESSED");
         AppendReasonCode(decision, "MOMENTUM_OK");
         AppendReasonCode(decision, "EXPANSION_OK");
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

      if(rates[0].close < lowerBand && expansionOk && momentumOk)
      {
         double stopLoss = MathMax(rates[0].high, vwap + (atr * 0.25));
         double takeProfit = rates[0].close - ((stopLoss - rates[0].close) * 1.5);
         SetEntryIntentDecision(
            decision,
            SIGNAL_ENTER_SHORT_INTENT,
            strategyName,
            symbol,
            analysisTimeframe,
            "BAND_BREAK_DOWN",
            "monitor-only short intent: derived noise-band break plus expansion and normalized momentum",
            now,
            stopLoss,
            takeProfit,
            MathMin(1.0, normalizedMomentum)
         );
         SetSuggestedEntry(decision, rates[0].close);
         AppendReasonCode(decision, "BAND_COMPRESSED");
         AppendReasonCode(decision, "MOMENTUM_OK");
         AppendReasonCode(decision, "EXPANSION_OK");
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
         "REENTRY_FAIL",
         "derived monitor-only noise-band rule is waiting for closed M5 break, expansion, and momentum",
         now,
         0.0
      );
      AppendReasonCode(decision, "BAND_COMPRESSED");
      if(!momentumOk)
         AppendReasonCode(decision, "MOMENTUM_OK");
      if(!expansionOk)
         AppendReasonCode(decision, "EXPANSION_OK");
      AppendReasonCode(decision, "WHIPSAW_BLOCK");
      AppendReasonCode(decision, "VWAP_FLAT_BLOCK");
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

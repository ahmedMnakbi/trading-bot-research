#ifndef UPCOMERS_NY_SESSION_PROP_BOT_VWAP_TREND_CONTINUATION_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_VWAP_TREND_CONTINUATION_MQH

#include "StrategyBase.mqh"
#include "SessionManager.mqh"

class CVWAPTrendContinuationStrategy
{
private:
   datetime m_lastSignalAt;
   string m_lastSignalDirection;
   int m_lastSignalSessionKey;
   int m_signalsThisSession;

   bool CooldownActive(const datetime now, const string direction, const int cooldownSeconds)
   {
      if(m_lastSignalAt <= 0)
         return false;
      if(m_lastSignalDirection != direction)
         return false;
      return (now - m_lastSignalAt) < cooldownSeconds;
   }

   void MarkSignal(const datetime now, const string direction)
   {
      m_lastSignalAt = now;
      m_lastSignalDirection = direction;
      m_signalsThisSession++;
   }

   double ClosedBarTypicalPrice(const MqlRates &bar)
   {
      return (bar.high + bar.low + bar.close) / 3.0;
   }

   double CalculateClosedBarVwap(const MqlRates &rates[], const int start, const int count)
   {
      double weightedPriceVolume = 0.0;
      double totalVolume = 0.0;
      for(int i = start; i < start + count; i++)
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

   double CalculateClosedBarAtr(const MqlRates &rates[], const int start, const int count)
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

   int CountVwapCrosses(const MqlRates &rates[], const int lookback, const double vwap)
   {
      int crosses = 0;
      bool previousAbove = rates[lookback - 1].close > vwap;
      for(int i = lookback - 2; i >= 0; i--)
      {
         bool above = rates[i].close > vwap;
         if(above != previousAbove)
            crosses++;
         previousAbove = above;
      }
      return crosses;
   }

public:
   CVWAPTrendContinuationStrategy()
   {
      m_lastSignalAt = 0;
      m_lastSignalDirection = "NONE";
      m_lastSignalSessionKey = 0;
      m_signalsThisSession = 0;
   }

   void Evaluate(
      const string symbol,
      const ENUM_TIMEFRAMES timeframe,
      const datetime now,
      CSessionManager &sessionManager,
      SStrategyDecision &decision,
      const int lookbackBars = 30,
      const double stopBufferPoints = 20.0,
      const int signalCooldownSeconds = 900,
      const int maxSignalsPerSession = 1,
      const int minHoldSeconds = 180
   )
   {
      const string strategyName = "VWAPTrendContinuation";
      const ENUM_TIMEFRAMES analysisTimeframe = PERIOD_M5;
      const double impulseAtrMultiple = 0.80;
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
            timeframe,
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
         m_lastSignalDirection = "NONE";
      }
      if(m_signalsThisSession >= maxSignalsPerSession)
      {
         SetWaitDecision(decision, "VWAP_SESSION_SIGNAL_CAP: max one signal per strategy/session");
         PopulateStrategyDecision(decision, strategyName, symbol, analysisTimeframe, "VWAP_SIGNAL_COOLDOWN", now);
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
      int barsNeeded = lookbackBars;
      if(barsNeeded < 20)
         barsNeeded = 20;
      int bars = CopyRates(symbol, analysisTimeframe, UPCOMERS_CLOSED_BAR_SHIFT, barsNeeded, rates);
      if(bars < 20)
      {
         SetSkipDecision(
            decision,
            SIGNAL_SKIP_DATA,
            strategyName,
            symbol,
            analysisTimeframe,
            "SKIP_DATA_VWAP_BARS",
            "session-reset VWAP logic needs at least twenty closed M5 bars",
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

      double vwap = CalculateClosedBarVwap(rates, 0, bars);
      double previousVwap = CalculateClosedBarVwap(rates, 1, bars - 1);
      if(vwap <= 0.0 || previousVwap <= 0.0)
      {
         SetSkipDecision(
            decision,
            SIGNAL_SKIP_DATA,
            strategyName,
            symbol,
            analysisTimeframe,
            "SKIP_DATA_ZERO_VOLUME",
            "VWAP skipped because volume is zero",
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

      double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
      if(point <= 0.0)
      {
         SetSkipDecision(
            decision,
            SIGNAL_SKIP_DATA,
            strategyName,
            symbol,
            analysisTimeframe,
            "SKIP_DATA_POINT_SIZE",
            "symbol point size unavailable for VWAP stop buffer",
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

      double buffer = stopBufferPoints * point;
      double atr = CalculateClosedBarAtr(rates, 0, 14);
      if(atr <= 0.0)
      {
         SetSkipDecision(
            decision,
            SIGNAL_SKIP_DATA,
            strategyName,
            symbol,
            analysisTimeframe,
            "SKIP_DATA_ATR",
            "VWAP impulse check needs positive ATR from closed M5 bars",
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

      double close0 = rates[0].close;
      double priorHigh = rates[1].high;
      double priorLow = rates[1].low;
      double vwapSlope = vwap - previousVwap;
      int crossLookback = lookbackBars;
      if(crossLookback > bars)
         crossLookback = bars;
      int crosses = CountVwapCrosses(rates, crossLookback, vwap);
      if(MathAbs(vwapSlope) < point || crosses > 6)
      {
         SetSetupFormingDecision(
            decision,
            strategyName,
            symbol,
            analysisTimeframe,
            "VWAP_FLAT_BLOCK",
            "VWAP_FLAT_BLOCK: VWAP flat/choppy or crosses too frequently",
            now,
            0.0
         );
         AppendReasonCode(decision, "CHOP_BLOCK");
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

      bool longBias = close0 > vwap && vwapSlope > 0.0;
      bool shortBias = close0 < vwap && vwapSlope < 0.0;
      double impulseLong = MathAbs(rates[3].high - vwap);
      double impulseShort = MathAbs(vwap - rates[3].low);
      bool impulseLongOk = impulseLong >= atr * impulseAtrMultiple;
      bool impulseShortOk = impulseShort >= atr * impulseAtrMultiple;
      bool pullbackLong = priorLow <= vwap + buffer && priorLow >= vwap - (buffer * 3.0);
      bool pullbackShort = priorHigh >= vwap - buffer && priorHigh <= vwap + (buffer * 3.0);
      bool rejectionLong = close0 > vwap && close0 > priorHigh;
      bool rejectionShort = close0 < vwap && close0 < priorLow;

      if(longBias && impulseLongOk && pullbackLong && rejectionLong)
      {
         if(CooldownActive(now, "LONG", signalCooldownSeconds))
         {
            SetWaitDecision(decision, "VWAP_SIGNAL_COOLDOWN: repeated long intent suppressed");
            PopulateStrategyDecision(decision, strategyName, symbol, analysisTimeframe, "VWAP_SIGNAL_COOLDOWN", now);
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
         double stopLoss = MathMin(priorLow, vwap - buffer);
         double takeProfit = close0 + ((close0 - stopLoss) * 1.5);
         if(stopLoss <= 0.0)
         {
            SetWaitDecision(decision, "VWAP_NO_STOP_LOSS: long intent blocked");
            PopulateStrategyDecision(decision, strategyName, symbol, analysisTimeframe, "VWAP_NO_STOP_LOSS", now);
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
         SetEntryIntentDecision(
            decision,
            SIGNAL_ENTER_LONG_INTENT,
            strategyName,
            symbol,
            analysisTimeframe,
            "REJECTION_CLOSE_OK",
            "monitor-only long intent: directional control, VWAP slope, impulse, pullback, and rejection confirmed",
            now,
            stopLoss,
            takeProfit,
            MathMin(1.0, MathAbs(close0 - vwap) / MathMax(point, buffer))
         );
         SetSuggestedEntry(decision, close0);
         AppendReasonCode(decision, "VWAP_BIAS_LONG");
         AppendReasonCode(decision, "VWAP_SLOPE_OK");
         AppendReasonCode(decision, "PULLBACK_NEAR_VWAP");
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
         MarkSignal(now, "LONG");
         return;
      }

      if(shortBias && impulseShortOk && pullbackShort && rejectionShort)
      {
         if(CooldownActive(now, "SHORT", signalCooldownSeconds))
         {
            SetWaitDecision(decision, "VWAP_SIGNAL_COOLDOWN: repeated short intent suppressed");
            PopulateStrategyDecision(decision, strategyName, symbol, analysisTimeframe, "VWAP_SIGNAL_COOLDOWN", now);
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
         double stopLoss = MathMax(priorHigh, vwap + buffer);
         double takeProfit = close0 - ((stopLoss - close0) * 1.5);
         if(stopLoss <= 0.0)
         {
            SetWaitDecision(decision, "VWAP_NO_STOP_LOSS: short intent blocked");
            PopulateStrategyDecision(decision, strategyName, symbol, analysisTimeframe, "VWAP_NO_STOP_LOSS", now);
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
         SetEntryIntentDecision(
            decision,
            SIGNAL_ENTER_SHORT_INTENT,
            strategyName,
            symbol,
            analysisTimeframe,
            "REJECTION_CLOSE_OK",
            "monitor-only short intent: directional control, VWAP slope, impulse, pullback, and rejection confirmed",
            now,
            stopLoss,
            takeProfit,
            MathMin(1.0, MathAbs(close0 - vwap) / MathMax(point, buffer))
         );
         SetSuggestedEntry(decision, close0);
         AppendReasonCode(decision, "VWAP_BIAS_SHORT");
         AppendReasonCode(decision, "VWAP_SLOPE_OK");
         AppendReasonCode(decision, "PULLBACK_NEAR_VWAP");
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
         MarkSignal(now, "SHORT");
         return;
      }

      string reasonCode = "VWAP_SETUP_FORMING";
      if(!impulseLongOk && !impulseShortOk)
         reasonCode = "IMPULSE_MISSING";
      else if((longBias || shortBias) && !(pullbackLong || pullbackShort))
         reasonCode = "PULLBACK_NEAR_VWAP";
      else if((pullbackLong || pullbackShort) && !(rejectionLong || rejectionShort))
         reasonCode = "REJECTION_CLOSE_OK";

      SetSetupFormingDecision(
         decision,
         strategyName,
         symbol,
         analysisTimeframe,
         reasonCode,
         "VWAP available but impulse, pullback, or rejection confirmation is incomplete",
         now,
         MathMin(1.0, MathAbs(close0 - vwap) / MathMax(point, buffer))
      );
      if(longBias)
         AppendReasonCode(decision, "VWAP_BIAS_LONG");
      if(shortBias)
         AppendReasonCode(decision, "VWAP_BIAS_SHORT");
      if(MathAbs(vwapSlope) >= point)
         AppendReasonCode(decision, "VWAP_SLOPE_OK");
      if(pullbackLong || pullbackShort)
         AppendReasonCode(decision, "PULLBACK_NEAR_VWAP");
      if(!impulseLongOk && !impulseShortOk)
         AppendReasonCode(decision, "IMPULSE_MISSING");
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

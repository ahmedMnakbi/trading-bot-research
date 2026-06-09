#ifndef UPCOMERS_NY_SESSION_PROP_BOT_OPENING_RANGE_BREAKOUT_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_OPENING_RANGE_BREAKOUT_MQH

#include "StrategyBase.mqh"
#include "SessionManager.mqh"

// Reason marker reserved for upstream spread gate failures: SPREAD_BLOCK.

class COpeningRangeBreakoutStrategy
{
private:
   int m_lastSignalSessionKey;
   string m_lastSignalSymbol;
   string m_lastSetupFingerprint;
   bool m_signalEmittedThisSession;
   int m_signalsThisSession;

   void MarkSignalEmitted(const string symbol, const int sessionKey)
   {
      m_lastSignalSymbol = symbol;
      m_lastSignalSessionKey = sessionKey;
      m_signalEmittedThisSession = true;
      m_signalsThisSession++;
   }

   int OpeningRangeMinutesToM1Bars(const int openingRangeMinutes)
   {
      if(openingRangeMinutes < 5)
         return 5;
      return openingRangeMinutes;
   }

   double AverageClosedBarRange(const MqlRates &rates[], const int start, const int count)
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

   bool DuplicateSetupBlocked(const string fingerprint)
   {
      if(m_lastSetupFingerprint == fingerprint)
         return true;
      m_lastSetupFingerprint = fingerprint;
      return false;
   }

public:
   COpeningRangeBreakoutStrategy()
   {
      m_lastSignalSessionKey = 0;
      m_lastSignalSymbol = "";
      m_lastSetupFingerprint = "";
      m_signalEmittedThisSession = false;
      m_signalsThisSession = 0;
   }

   void Evaluate(
      const string symbol,
      const ENUM_TIMEFRAMES timeframe,
      const datetime now,
      CSessionManager &sessionManager,
      SStrategyDecision &decision,
      const int openingRangeMinutes = 15,
      const double minimumRangePoints = 10.0,
      const double takeProfitR = 2.0,
      const int retestWindowBars = 3,
      const int maxSignalsPerSession = 1,
      const int minHoldSeconds = 180
   )
   {
      const string strategyName = "OpeningRangeBreakout";
      const ENUM_TIMEFRAMES rangeTimeframe = PERIOD_M1;
      const bool defaultBreakThenRetestMode = true;
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
            "VOLUME_NOT_USED"
         );
         AppendReasonCode(decision, "NEWS_BLOCK");
         return;
      }

      const int sessionKey = sessionManager.StrategySessionKey(now);
      if(m_lastSignalSessionKey != sessionKey)
      {
         m_signalsThisSession = 0;
         m_signalEmittedThisSession = false;
         m_lastSetupFingerprint = "";
      }
      if(m_signalEmittedThisSession &&
         m_lastSignalSessionKey == sessionKey &&
         m_lastSignalSymbol == symbol)
      {
         SetWaitDecision(decision, "ORB_SIGNAL_COOLDOWN: same-symbol session signal already emitted");
         PopulateStrategyDecision(decision, strategyName, symbol, timeframe, "ORB_SIGNAL_COOLDOWN", now);
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            "VOLUME_NOT_USED"
         );
         return;
      }
      if(m_signalsThisSession >= maxSignalsPerSession)
      {
         SetWaitDecision(decision, "ORB_SESSION_SIGNAL_CAP: max one signal per symbol/session by default");
         PopulateStrategyDecision(decision, strategyName, symbol, timeframe, "ORB_SESSION_SIGNAL_CAP", now);
         AppendReasonCode(decision, "LATE_SIGNAL_BLOCK");
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            "VOLUME_NOT_USED"
         );
         return;
      }

      if(openingRangeMinutes < 5)
      {
         SetSkipDecision(
            decision,
            SIGNAL_SKIP_DATA,
            strategyName,
            symbol,
            timeframe,
            "SKIP_DATA_INVALID_RANGE_MINUTES",
            "opening range minutes must be at least 5",
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
            "VOLUME_NOT_USED"
         );
         return;
      }

      MqlRates rates[];
      ArraySetAsSeries(rates, true);
      int rangeBars = OpeningRangeMinutesToM1Bars(openingRangeMinutes);
      int safeRetestWindowBars = retestWindowBars;
      if(safeRetestWindowBars < 1)
         safeRetestWindowBars = 1;
      int barsNeeded = rangeBars + safeRetestWindowBars + 4;
      int bars = CopyRates(symbol, rangeTimeframe, UPCOMERS_CLOSED_BAR_SHIFT, barsNeeded, rates);
      if(bars < barsNeeded)
      {
         SetSkipDecision(
            decision,
            SIGNAL_SKIP_DATA,
            strategyName,
            symbol,
            rangeTimeframe,
            "SKIP_DATA_OPENING_RANGE_INCOMPLETE",
            "opening range completion logic needs closed M1 bars from session start",
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
            "VOLUME_NOT_USED"
         );
         return;
      }

      const int rangeStartShift = safeRetestWindowBars + 2;
      double rangeHigh = rates[rangeStartShift].high;
      double rangeLow = rates[rangeStartShift].low;
      for(int i = rangeStartShift; i < rangeStartShift + rangeBars; i++)
      {
         if(rates[i].high > rangeHigh)
            rangeHigh = rates[i].high;
         if(rates[i].low < rangeLow)
            rangeLow = rates[i].low;
      }

      double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
      if(point <= 0.0)
      {
         SetSkipDecision(
            decision,
            SIGNAL_SKIP_DATA,
            strategyName,
            symbol,
            timeframe,
            "SKIP_DATA_POINT_SIZE",
            "symbol point size unavailable",
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
            "VOLUME_NOT_USED"
         );
         return;
      }

      double rangePoints = (rangeHigh - rangeLow) / point;
      double closedRangeAtr = AverageClosedBarRange(rates, rangeStartShift, rangeBars);
      double rangeWidth = rangeHigh - rangeLow;
      if(rangePoints < minimumRangePoints)
      {
         SetWaitDecision(decision, "ORB_TINY_RANGE: opening range below configured minimum");
         PopulateStrategyDecision(decision, strategyName, symbol, rangeTimeframe, "ORB_TINY_RANGE", now);
         decision.QualityScore = rangePoints / minimumRangePoints;
         AppendReasonCode(decision, "RETEST_FAIL");
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            "VOLUME_NOT_USED"
         );
         return;
      }
      if(closedRangeAtr > 0.0 && (rangeWidth < closedRangeAtr * 0.25 || rangeWidth > closedRangeAtr * 6.0))
      {
         SetWaitDecision(decision, "ORB_WIDTH_BLOCK: range width outside ATR-relative bounds");
         PopulateStrategyDecision(decision, strategyName, symbol, rangeTimeframe, "ORB_WIDTH_BLOCK", now);
         AppendReasonCode(decision, "ORB_RANGE_BUILT");
         AppendReasonCode(decision, "RETEST_FAIL");
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            "VOLUME_NOT_USED"
         );
         return;
      }

      const double buffer = MathMax(point, point * 2.0);
      MqlRates retestBar = rates[0];
      MqlRates breakoutBar = rates[1];
      double longEntry = retestBar.close;
      double shortEntry = retestBar.close;
      string setupFingerprint = StringFormat(
         "%s:%d:%.5f:%.5f",
         symbol,
         sessionKey,
         rangeHigh,
         rangeLow
      );

      bool longBreakClosedOutside = breakoutBar.close > rangeHigh + buffer;
      bool longRetestPass = retestBar.low <= rangeHigh + buffer && retestBar.close > rangeHigh;
      bool shortBreakClosedOutside = breakoutBar.close < rangeLow - buffer;
      bool shortRetestPass = retestBar.high >= rangeLow - buffer && retestBar.close < rangeLow;

      if(defaultBreakThenRetestMode && DuplicateSetupBlocked(setupFingerprint))
      {
         SetWaitDecision(decision, "ORB_SIGNAL_COOLDOWN: repeated setup fingerprint suppressed");
         PopulateStrategyDecision(decision, strategyName, symbol, rangeTimeframe, "ORB_SIGNAL_COOLDOWN", now);
         AppendReasonCode(decision, "ORB_RANGE_BUILT");
         AppendReasonCode(decision, "ORB_WIDTH_OK");
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            "VOLUME_NOT_USED"
         );
         return;
      }

      if(longBreakClosedOutside && longRetestPass)
      {
         double stopLoss = MathMin(retestBar.low, breakoutBar.low) - buffer;
         double takeProfit = longEntry + ((longEntry - stopLoss) * takeProfitR);
         if(stopLoss <= 0.0)
         {
            SetWaitDecision(decision, "ORB_NO_STOP_LOSS: long intent blocked");
            PopulateStrategyDecision(decision, strategyName, symbol, rangeTimeframe, "ORB_NO_STOP_LOSS", now);
            SetDecisionContext(
               decision,
               symbolClass,
               sessionTag,
               newYorkTime,
               hasNewYorkTime,
               minHoldSeconds,
               "SPREAD_CHECKED_UPSTREAM",
               "VOLUME_NOT_USED"
            );
            return;
         }
         SetEntryIntentDecision(
            decision,
            SIGNAL_ENTER_LONG_INTENT,
            strategyName,
            symbol,
            rangeTimeframe,
            "BREAK_CLOSE_OUTSIDE",
            "monitor-only long intent: BreakThenRetest ORB confirmation on closed M1 bars",
            now,
            stopLoss,
            takeProfit,
            MathMin(1.0, rangePoints / (minimumRangePoints * 3.0))
         );
         SetSuggestedEntry(decision, longEntry);
         AppendReasonCode(decision, "ORB_RANGE_BUILT");
         AppendReasonCode(decision, "ORB_WIDTH_OK");
         AppendReasonCode(decision, "RETEST_PASS");
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            "VOLUME_NOT_USED"
         );
         MarkSignalEmitted(symbol, sessionKey);
         return;
      }

      if(shortBreakClosedOutside && shortRetestPass)
      {
         double stopLoss = MathMax(retestBar.high, breakoutBar.high) + buffer;
         double takeProfit = shortEntry - ((stopLoss - shortEntry) * takeProfitR);
         if(stopLoss <= 0.0)
         {
            SetWaitDecision(decision, "ORB_NO_STOP_LOSS: short intent blocked");
            PopulateStrategyDecision(decision, strategyName, symbol, rangeTimeframe, "ORB_NO_STOP_LOSS", now);
            SetDecisionContext(
               decision,
               symbolClass,
               sessionTag,
               newYorkTime,
               hasNewYorkTime,
               minHoldSeconds,
               "SPREAD_CHECKED_UPSTREAM",
               "VOLUME_NOT_USED"
            );
            return;
         }
         SetEntryIntentDecision(
            decision,
            SIGNAL_ENTER_SHORT_INTENT,
            strategyName,
            symbol,
            rangeTimeframe,
            "BREAK_CLOSE_OUTSIDE",
            "monitor-only short intent: BreakThenRetest ORB confirmation on closed M1 bars",
            now,
            stopLoss,
            takeProfit,
            MathMin(1.0, rangePoints / (minimumRangePoints * 3.0))
         );
         SetSuggestedEntry(decision, shortEntry);
         AppendReasonCode(decision, "ORB_RANGE_BUILT");
         AppendReasonCode(decision, "ORB_WIDTH_OK");
         AppendReasonCode(decision, "RETEST_PASS");
         SetDecisionContext(
            decision,
            symbolClass,
            sessionTag,
            newYorkTime,
            hasNewYorkTime,
            minHoldSeconds,
            "SPREAD_CHECKED_UPSTREAM",
            "VOLUME_NOT_USED"
         );
         MarkSignalEmitted(symbol, sessionKey);
         return;
      }

      string waitReason = "opening range complete; BreakThenRetest confirmation is incomplete";
      string reasonCode = "ORB_SETUP_FORMING";
      if((longBreakClosedOutside || shortBreakClosedOutside) && !(longRetestPass || shortRetestPass))
      {
         waitReason = "RETEST_FAIL: breakout closed outside but retest did not hold";
         reasonCode = "RETEST_FAIL";
      }
      if(retestBar.close < rangeHigh && retestBar.close > rangeLow)
      {
         AppendReasonCode(decision, "CLOSE_BACK_INSIDE");
      }

      SetSetupFormingDecision(
         decision,
         strategyName,
         symbol,
         rangeTimeframe,
         reasonCode,
         waitReason,
         now,
         MathMin(1.0, rangePoints / (minimumRangePoints * 3.0))
      );
      AppendReasonCode(decision, "ORB_RANGE_BUILT");
      AppendReasonCode(decision, "ORB_WIDTH_OK");
      if(retestBar.close < rangeHigh && retestBar.close > rangeLow)
         AppendReasonCode(decision, "CLOSE_BACK_INSIDE");
      SetDecisionContext(
         decision,
         symbolClass,
         sessionTag,
         newYorkTime,
         hasNewYorkTime,
         minHoldSeconds,
         "SPREAD_CHECKED_UPSTREAM",
         "VOLUME_NOT_USED"
      );
   }
};

#endif

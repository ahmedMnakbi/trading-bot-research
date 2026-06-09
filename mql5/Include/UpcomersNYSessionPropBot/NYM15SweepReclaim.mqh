#ifndef UPCOMERS_NY_SESSION_PROP_BOT_NY_M15_SWEEP_RECLAIM_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_NY_M15_SWEEP_RECLAIM_MQH

#include "StrategyBase.mqh"
#include "SessionManager.mqh"

// Reason marker reserved for upstream spread gate failures: SPREAD_BLOCK.

// Internal daily state phases (not exposed as MQL5 enum to keep file self-contained).
#define NYM15SR_PHASE_IDLE              0
#define NYM15SR_PHASE_CRT_CANDLE_SET    1
#define NYM15SR_PHASE_SWEEP_DETECTED    2
#define NYM15SR_PHASE_ENTRY_PENDING     3
#define NYM15SR_PHASE_TRADE_TAKEN       4
#define NYM15SR_PHASE_CANCELLED         5
#define NYM15SR_PHASE_SKIP_DAY          6

class CNYm15SweepReclaimStrategy
{
private:
   // Per-session daily state
   int      m_sessionKey;
   int      m_phase;
   bool     m_isBullish;
   double   m_m15High;
   double   m_m15Low;
   double   m_sweepExtreme;      // sweep high (bearish) or sweep low (bullish)
   datetime m_sweepBarTime;      // broker-time open of the M5 sweep candle
   double   m_reclaimLevel;      // reclaim candle low (bearish) or high (bullish)
   datetime m_reclaimBarTime;    // broker-time open of the M5 reclaim candle
   int      m_barsAfterSweep;    // closed M5 bar count since sweep detection
   datetime m_lastM5BarTime;     // guard: prevents re-processing same closed M5 bar

   // Cached H1 EMA indicator handle
   int      m_emaHandle;
   string   m_emaSymbol;
   int      m_emaPeriod;

   void ResetDailyState()
   {
      m_phase         = NYM15SR_PHASE_IDLE;
      m_isBullish     = false;
      m_m15High       = 0.0;
      m_m15Low        = 0.0;
      m_sweepExtreme  = 0.0;
      m_sweepBarTime  = 0;
      m_reclaimLevel  = 0.0;
      m_reclaimBarTime = 0;
      m_barsAfterSweep = 0;
      m_lastM5BarTime  = 0;
   }

   void ReleaseEmaHandle()
   {
      if(m_emaHandle != INVALID_HANDLE)
      {
         IndicatorRelease(m_emaHandle);
         m_emaHandle = INVALID_HANDLE;
         m_emaSymbol = "";
         m_emaPeriod = 0;
      }
   }

   bool GetH1EMA50(const string symbol, const int emaPeriod, double &emaValue)
   {
      emaValue = 0.0;
      if(m_emaHandle == INVALID_HANDLE || m_emaSymbol != symbol || m_emaPeriod != emaPeriod)
      {
         ReleaseEmaHandle();
         m_emaHandle = iEMA(symbol, PERIOD_H1, emaPeriod, 0, PRICE_CLOSE);
         if(m_emaHandle == INVALID_HANDLE)
            return false;
         m_emaSymbol = symbol;
         m_emaPeriod = emaPeriod;
      }
      double buf[];
      ArraySetAsSeries(buf, true);
      // bar[1] = last fully closed H1 bar; never use bar[0]
      if(CopyBuffer(m_emaHandle, 0, UPCOMERS_CLOSED_BAR_SHIFT, 1, buf) < 1)
         return false;
      emaValue = buf[0];
      return emaValue > 0.0;
   }

public:
   CNYm15SweepReclaimStrategy()
   {
      m_sessionKey = 0;
      m_emaHandle  = INVALID_HANDLE;
      m_emaSymbol  = "";
      m_emaPeriod  = 0;
      ResetDailyState();
   }

   ~CNYm15SweepReclaimStrategy()
   {
      ReleaseEmaHandle();
   }

   void Evaluate(
      const string symbol,
      const ENUM_TIMEFRAMES timeframe,
      const datetime now,
      CSessionManager &sessionManager,
      SStrategyDecision &decision,
      // Strategy parameters — defaults match spec exactly; these are not optimized values
      const int    nyOpenHour          = 9,
      const int    nyOpenMinute        = 30,
      const int    nyWindowEndHour     = 11,
      const int    nyWindowEndMinute   = 0,
      const int    emaPeriod           = 50,
      const double minCRTRangePoints   = 100.0,
      const double minSweepPoints      = 20.0,
      const double stopBufferPoints    = 50.0,
      const double takeProfitR         = 2.0,
      const int    maxBarsAfterSweep   = 12,
      const int    maxTradesPerDay     = 1,
      const int    minHoldSeconds      = 180
   )
   {
      const string strategyName = "NYM15SweepReclaim";
      const string spreadStatus = "SPREAD_CHECKED_UPSTREAM";
      const string volumeStatus = "VOLUME_NOT_USED";

      // --- Resolve NY time and context ---
      datetime nyTime     = 0;
      string   convReason = "";
      bool     hasNYTime  = sessionManager.TryConvertBrokerServerToNewYork(now, nyTime, convReason);
      string symbolClass  = sessionManager.SymbolClassFor(symbol);
      string sessionTag   = sessionManager.SessionTagForSymbol(symbol);

      if(!hasNYTime)
      {
         SetSkipDecision(decision, SIGNAL_SKIP_DATA, strategyName, symbol, timeframe,
            "SKIP_DATA_NY_TIME_UNAVAILABLE",
            "NY time conversion unavailable: " + convReason, now);
         SetDecisionContext(decision, symbolClass, sessionTag, 0, false,
            minHoldSeconds, spreadStatus, volumeStatus);
         return;
      }

      MqlDateTime nyParts;
      TimeToStruct(nyTime, nyParts);
      int nyMinuteOfDay      = nyParts.hour * 60 + nyParts.min;
      int nyDateKey          = nyParts.year * 10000 + nyParts.mon * 100 + nyParts.day;
      int nyOpenTotalMinute  = nyOpenHour * 60 + nyOpenMinute;
      int nyWindowEndMinute_ = nyWindowEndHour * 60 + nyWindowEndMinute;

      // --- Daily reset when the NY calendar date changes ---
      int sessionKey = sessionManager.StrategySessionKey(now);
      if(sessionKey != 0 && sessionKey != m_sessionKey)
      {
         ResetDailyState();
         m_sessionKey = sessionKey;
      }

      // --- Symbol metadata ---
      double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
      if(point <= 0.0)
      {
         SetSkipDecision(decision, SIGNAL_SKIP_DATA, strategyName, symbol, timeframe,
            "SKIP_DATA_POINT_SIZE", "symbol point size unavailable", now);
         SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
            minHoldSeconds, spreadStatus, volumeStatus);
         return;
      }

      // --- Already done for today ---
      if(m_phase == NYM15SR_PHASE_TRADE_TAKEN || m_phase == NYM15SR_PHASE_SKIP_DAY)
      {
         SetSkipDecision(decision, SIGNAL_SKIP_SESSION, strategyName, symbol, timeframe,
            m_phase == NYM15SR_PHASE_TRADE_TAKEN
               ? "NYM15SR_TRADE_TAKEN"
               : "NYM15SR_SKIP_DAY",
            "NY M15 sweep reclaim session complete for today", now);
         SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
            minHoldSeconds, spreadStatus, volumeStatus);
         return;
      }
      if(m_phase == NYM15SR_PHASE_CANCELLED)
      {
         m_phase = NYM15SR_PHASE_SKIP_DAY;
         SetSkipDecision(decision, SIGNAL_SKIP_SESSION, strategyName, symbol, timeframe,
            "NYM15SR_CANCELLED",
            "setup cancelled; skipping rest of session", now);
         SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
            minHoldSeconds, spreadStatus, volumeStatus);
         return;
      }

      // --- Before NY open ---
      if(nyMinuteOfDay < nyOpenTotalMinute)
      {
         SetWaitDecision(decision, "NYM15SR: waiting for NY 09:30 open");
         PopulateStrategyDecision(decision, strategyName, symbol, timeframe,
            "NYM15SR_BEFORE_WINDOW", now);
         SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
            minHoldSeconds, spreadStatus, volumeStatus);
         return;
      }

      // --- Window expiry cancels any active setup before TRADE_TAKEN ---
      if(nyMinuteOfDay >= nyWindowEndMinute_)
      {
         m_phase = NYM15SR_PHASE_CANCELLED;
         SetSkipDecision(decision, SIGNAL_SKIP_SESSION, strategyName, symbol, timeframe,
            "NYM15SR_WINDOW_EXPIRED",
            "11:00 NY window reached before entry intent; setup cancelled", now);
         SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
            minHoldSeconds, spreadStatus, volumeStatus);
         return;
      }

      // --- H1 EMA50 trend filter (last closed H1 bar only; H1[0] forbidden) ---
      double ema50 = 0.0;
      if(!GetH1EMA50(symbol, emaPeriod, ema50) || ema50 <= 0.0)
      {
         m_phase = NYM15SR_PHASE_SKIP_DAY;
         SetSkipDecision(decision, SIGNAL_SKIP_DATA, strategyName, symbol, timeframe,
            "NYM15SR_EMA_UNAVAILABLE",
            "H1 EMA50 unavailable or not yet calculated; skipping day", now);
         SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
            minHoldSeconds, spreadStatus, volumeStatus);
         return;
      }

      MqlRates h1Rates[];
      ArraySetAsSeries(h1Rates, true);
      // shift=1 → starts at bar[1]; h1Rates[0] is the last fully closed H1 bar
      if(CopyRates(symbol, PERIOD_H1, UPCOMERS_CLOSED_BAR_SHIFT, 2, h1Rates) < 1)
      {
         m_phase = NYM15SR_PHASE_SKIP_DAY;
         SetSkipDecision(decision, SIGNAL_SKIP_DATA, strategyName, symbol, timeframe,
            "NYM15SR_H1_DATA_UNAVAILABLE",
            "H1 bar data unavailable; skipping day", now);
         SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
            minHoldSeconds, spreadStatus, volumeStatus);
         return;
      }
      double h1LastClose = h1Rates[0].close; // last closed H1 bar

      bool h1Bullish = h1LastClose > ema50;
      bool h1Bearish = h1LastClose < ema50;
      if(!h1Bullish && !h1Bearish)
      {
         // H1 close equals EMA50 exactly → no clear trend; skip day
         m_phase = NYM15SR_PHASE_SKIP_DAY;
         SetSkipDecision(decision, SIGNAL_SKIP_SESSION, strategyName, symbol, timeframe,
            "NYM15SR_H1_NEUTRAL",
            "last closed H1 close equals EMA50; no clear trend; skipping day", now);
         SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
            minHoldSeconds, spreadStatus, volumeStatus);
         return;
      }

      // =====================================================================
      // IDLE: find first fully closed M15 candle in NY window
      // =====================================================================
      if(m_phase == NYM15SR_PHASE_IDLE)
      {
         MqlRates m15[];
         ArraySetAsSeries(m15, true);
         // shift=1 → all returned bars are fully closed; 20 bars covers ~5 hours
         int m15Count = CopyRates(symbol, PERIOD_M15, UPCOMERS_CLOSED_BAR_SHIFT, 20, m15);
         if(m15Count < 1)
         {
            SetSetupFormingDecision(decision, strategyName, symbol, timeframe,
               "NYM15SR_WAITING_M15_DATA",
               "waiting for M15 bar data", now);
            SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
               minHoldSeconds, spreadStatus, volumeStatus);
            return;
         }

         // Iterate oldest → newest (high index → low index in ArraySetAsSeries)
         // to find the FIRST M15 bar that opened on today's NY date at or after 09:30
         int setupBarIdx = -1;
         for(int i = m15Count - 1; i >= 0; i--)
         {
            datetime barNY = 0;
            string   bcr   = "";
            if(!sessionManager.TryConvertBrokerServerToNewYork(m15[i].time, barNY, bcr))
               continue;
            MqlDateTime bp;
            TimeToStruct(barNY, bp);
            int barDateKey = bp.year * 10000 + bp.mon * 100 + bp.day;
            int barMin     = bp.hour * 60 + bp.min;
            if(barDateKey != nyDateKey)
               continue;
            if(barMin >= nyOpenTotalMinute)
            {
               setupBarIdx = i; // oldest qualifying bar = first in window
               break;
            }
         }

         if(setupBarIdx < 0)
         {
            // Inside window but no closed M15 bar after 09:30 yet
            SetSetupFormingDecision(decision, strategyName, symbol, timeframe,
               "NYM15SR_WAITING_FIRST_M15",
               "inside NY window; waiting for first closed M15 candle at or after 09:30", now);
            SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
               minHoldSeconds, spreadStatus, volumeStatus);
            return;
         }

         // Evaluate the first M15 setup candle
         MqlRates setupBar = m15[setupBarIdx];
         double   m15Range = (setupBar.high - setupBar.low) / point;
         bool     m15Bull  = setupBar.close > setupBar.open;
         bool     m15Bear  = setupBar.close < setupBar.open;

         if(m15Range < minCRTRangePoints)
         {
            m_phase = NYM15SR_PHASE_SKIP_DAY;
            SetSkipDecision(decision, SIGNAL_SKIP_SESSION, strategyName, symbol, timeframe,
               "NYM15SR_CRT_RANGE_TOO_SMALL",
               StringFormat(
                  "first M15 candle range %.1f points below minimum %.1f; skipping day",
                  m15Range, minCRTRangePoints),
               now);
            SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
               minHoldSeconds, spreadStatus, volumeStatus);
            return;
         }

         // Direction must match H1 trend; "do not keep searching for later M15 candles"
         bool directionMatch = (h1Bullish && m15Bull) || (h1Bearish && m15Bear);
         if(!directionMatch)
         {
            m_phase = NYM15SR_PHASE_SKIP_DAY;
            SetSkipDecision(decision, SIGNAL_SKIP_SESSION, strategyName, symbol, timeframe,
               "NYM15SR_M15_DISAGREES_WITH_H1",
               "first M15 candle direction disagrees with H1 EMA50 trend; skipping day", now);
            SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
               minHoldSeconds, spreadStatus, volumeStatus);
            return;
         }

         m_isBullish = h1Bullish;
         m_m15High   = setupBar.high;
         m_m15Low    = setupBar.low;
         m_phase     = NYM15SR_PHASE_CRT_CANDLE_SET;

         // Return SETUP_FORMING; sweep detection begins on the next bar evaluation.
         SetSetupFormingDecision(decision, strategyName, symbol, timeframe,
            "NYM15SR_CRT_CANDLE_SET",
            StringFormat(
               "first M15 candle set: direction=%s H=%.5f L=%.5f; waiting for M5 sweep",
               m_isBullish ? "BULLISH" : "BEARISH",
               m_m15High, m_m15Low),
            now);
         SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
            minHoldSeconds, spreadStatus, volumeStatus);
         return;
      }

      // =====================================================================
      // CRT_CANDLE_SET: wait for first M5 candle to sweep beyond M15 level
      // =====================================================================
      if(m_phase == NYM15SR_PHASE_CRT_CANDLE_SET)
      {
         MqlRates m5[];
         ArraySetAsSeries(m5, true);
         if(CopyRates(symbol, PERIOD_M5, UPCOMERS_CLOSED_BAR_SHIFT, 2, m5) < 1)
         {
            SetSetupFormingDecision(decision, strategyName, symbol, timeframe,
               "NYM15SR_CRT_CANDLE_SET", "CRT set; waiting for M5 sweep", now);
            SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
               minHoldSeconds, spreadStatus, volumeStatus);
            return;
         }
         MqlRates bar = m5[0]; // last fully closed M5 bar

         if(bar.time == m_lastM5BarTime)
         {
            SetSetupFormingDecision(decision, strategyName, symbol, timeframe,
               "NYM15SR_CRT_CANDLE_SET", "CRT set; waiting for M5 sweep", now);
            SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
               minHoldSeconds, spreadStatus, volumeStatus);
            return;
         }
         m_lastM5BarTime = bar.time;

         bool sweep = false;
         if(m_isBullish)
         {
            double sweepThreshold = m_m15Low - (minSweepPoints * point);
            if(bar.low < sweepThreshold)
            {
               m_sweepExtreme = bar.low;
               m_sweepBarTime = bar.time;
               m_barsAfterSweep = 0;
               m_phase = NYM15SR_PHASE_SWEEP_DETECTED;
               sweep = true;
            }
         }
         else
         {
            double sweepThreshold = m_m15High + (minSweepPoints * point);
            if(bar.high > sweepThreshold)
            {
               m_sweepExtreme = bar.high;
               m_sweepBarTime = bar.time;
               m_barsAfterSweep = 0;
               m_phase = NYM15SR_PHASE_SWEEP_DETECTED;
               sweep = true;
            }
         }

         if(sweep)
         {
            SetSetupFormingDecision(decision, strategyName, symbol, timeframe,
               "NYM15SR_SWEEP_DETECTED",
               StringFormat(
                  "M5 sweep detected at %.5f; waiting for reclaim of M15 %s",
                  m_sweepExtreme,
                  m_isBullish ? "low" : "high"),
               now);
         }
         else
         {
            SetSetupFormingDecision(decision, strategyName, symbol, timeframe,
               "NYM15SR_CRT_CANDLE_SET",
               StringFormat(
                  "CRT set %s H=%.5f L=%.5f; no M5 sweep yet",
                  m_isBullish ? "BULLISH" : "BEARISH",
                  m_m15High, m_m15Low),
               now);
         }
         SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
            minHoldSeconds, spreadStatus, volumeStatus);
         return;
      }

      // =====================================================================
      // SWEEP_DETECTED: wait for a DIFFERENT M5 candle to reclaim the M15 level
      // =====================================================================
      if(m_phase == NYM15SR_PHASE_SWEEP_DETECTED)
      {
         MqlRates m5[];
         ArraySetAsSeries(m5, true);
         if(CopyRates(symbol, PERIOD_M5, UPCOMERS_CLOSED_BAR_SHIFT, 2, m5) < 1)
         {
            SetSetupFormingDecision(decision, strategyName, symbol, timeframe,
               "NYM15SR_SWEEP_DETECTED",
               "sweep active; waiting for M5 reclaim bar", now);
            SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
               minHoldSeconds, spreadStatus, volumeStatus);
            return;
         }
         MqlRates bar = m5[0];

         if(bar.time == m_lastM5BarTime)
         {
            SetSetupFormingDecision(decision, strategyName, symbol, timeframe,
               "NYM15SR_SWEEP_DETECTED",
               "sweep active; waiting for next closed M5 bar", now);
            SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
               minHoldSeconds, spreadStatus, volumeStatus);
            return;
         }
         m_lastM5BarTime = bar.time;
         m_barsAfterSweep++;

         if(m_barsAfterSweep > maxBarsAfterSweep)
         {
            m_phase = NYM15SR_PHASE_CANCELLED;
            SetSkipDecision(decision, SIGNAL_SKIP_SESSION, strategyName, symbol, timeframe,
               "NYM15SR_MAX_BARS_AFTER_SWEEP",
               StringFormat(
                  "more than %d bars after sweep without reclaim; setup cancelled",
                  maxBarsAfterSweep),
               now);
            SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
               minHoldSeconds, spreadStatus, volumeStatus);
            return;
         }

         // Reclaim candle must be a DIFFERENT bar from the sweep candle
         if(bar.time == m_sweepBarTime)
         {
            SetSetupFormingDecision(decision, strategyName, symbol, timeframe,
               "NYM15SR_SWEEP_DETECTED",
               "same bar as sweep; waiting for different M5 candle for reclaim", now);
            SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
               minHoldSeconds, spreadStatus, volumeStatus);
            return;
         }

         bool reclaim = false;
         if(m_isBullish)
         {
            // Bullish reclaim: close back above M15 low on a different M5 bar
            if(bar.close > m_m15Low)
            {
               m_reclaimLevel   = bar.high; // reclaim candle high = entry trigger
               m_reclaimBarTime = bar.time;
               m_phase          = NYM15SR_PHASE_ENTRY_PENDING;
               reclaim          = true;
            }
         }
         else
         {
            // Bearish reclaim: close back below M15 high on a different M5 bar
            if(bar.close < m_m15High)
            {
               m_reclaimLevel   = bar.low; // reclaim candle low = entry trigger
               m_reclaimBarTime = bar.time;
               m_phase          = NYM15SR_PHASE_ENTRY_PENDING;
               reclaim          = true;
            }
         }

         if(reclaim)
         {
            SetSetupFormingDecision(decision, strategyName, symbol, timeframe,
               "NYM15SR_RECLAIM_CONFIRMED",
               StringFormat(
                  "M5 reclaim confirmed; entry trigger at %.5f; waiting for M5 breakout",
                  m_reclaimLevel),
               now);
         }
         else
         {
            SetSetupFormingDecision(decision, strategyName, symbol, timeframe,
               "NYM15SR_SWEEP_DETECTED",
               StringFormat(
                  "sweep at %.5f; bars since sweep=%d; no reclaim yet",
                  m_sweepExtreme, m_barsAfterSweep),
               now);
         }
         SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
            minHoldSeconds, spreadStatus, volumeStatus);
         return;
      }

      // =====================================================================
      // ENTRY_PENDING: wait for closed M5 candle to break the reclaim level
      // =====================================================================
      if(m_phase == NYM15SR_PHASE_ENTRY_PENDING)
      {
         MqlRates m5[];
         ArraySetAsSeries(m5, true);
         if(CopyRates(symbol, PERIOD_M5, UPCOMERS_CLOSED_BAR_SHIFT, 2, m5) < 1)
         {
            SetSetupFormingDecision(decision, strategyName, symbol, timeframe,
               "NYM15SR_ENTRY_PENDING",
               StringFormat("reclaim confirmed at %.5f; waiting for entry trigger", m_reclaimLevel),
               now);
            SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
               minHoldSeconds, spreadStatus, volumeStatus);
            return;
         }
         MqlRates bar = m5[0];

         if(bar.time == m_lastM5BarTime)
         {
            SetSetupFormingDecision(decision, strategyName, symbol, timeframe,
               "NYM15SR_ENTRY_PENDING",
               StringFormat("waiting for entry trigger at %.5f", m_reclaimLevel), now);
            SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
               minHoldSeconds, spreadStatus, volumeStatus);
            return;
         }
         m_lastM5BarTime = bar.time;

         // Entry bar must be different from the reclaim bar
         if(bar.time == m_reclaimBarTime)
         {
            SetSetupFormingDecision(decision, strategyName, symbol, timeframe,
               "NYM15SR_ENTRY_PENDING",
               "same bar as reclaim; waiting for different M5 candle for entry", now);
            SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
               minHoldSeconds, spreadStatus, volumeStatus);
            return;
         }

         bool triggered = false;
         ENUM_UPCOMERS_SIGNAL entrySignal = SIGNAL_WAIT;
         double stopLoss   = 0.0;
         double takeProfit = 0.0;
         double entryPrice = 0.0;

         if(m_isBullish)
         {
            if(bar.close > m_reclaimLevel)
            {
               entryPrice = bar.close;
               stopLoss   = m_sweepExtreme - (stopBufferPoints * point);
               double risk = entryPrice - stopLoss;
               if(risk > 0.0)
               {
                  takeProfit  = entryPrice + (risk * takeProfitR);
                  entrySignal = SIGNAL_ENTER_LONG_INTENT;
                  triggered   = true;
               }
            }
         }
         else
         {
            if(bar.close < m_reclaimLevel)
            {
               entryPrice = bar.close;
               stopLoss   = m_sweepExtreme + (stopBufferPoints * point);
               double risk = stopLoss - entryPrice;
               if(risk > 0.0)
               {
                  takeProfit  = entryPrice - (risk * takeProfitR);
                  if(takeProfit <= 0.0)
                     takeProfit = 0.0; // safety floor; will be blocked by SL check below
                  entrySignal = SIGNAL_ENTER_SHORT_INTENT;
                  triggered   = true;
               }
            }
         }

         if(!triggered)
         {
            SetSetupFormingDecision(decision, strategyName, symbol, timeframe,
               "NYM15SR_ENTRY_PENDING",
               StringFormat("entry pending; breakout trigger at %.5f not yet reached",
                  m_reclaimLevel),
               now);
            SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
               minHoldSeconds, spreadStatus, volumeStatus);
            return;
         }

         if(stopLoss <= 0.0)
         {
            m_phase = NYM15SR_PHASE_CANCELLED;
            SetSkipDecision(decision, SIGNAL_SKIP_DATA, strategyName, symbol, timeframe,
               "NYM15SR_INVALID_STOP_LOSS",
               "stop loss could not be computed as a positive distance; setup cancelled", now);
            SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
               minHoldSeconds, spreadStatus, volumeStatus);
            return;
         }

         m_phase = NYM15SR_PHASE_TRADE_TAKEN;

         string reasonCode = entrySignal == SIGNAL_ENTER_LONG_INTENT
            ? "NYM15SR_ENTER_LONG_INTENT"
            : "NYM15SR_ENTER_SHORT_INTENT";

         SetEntryIntentDecision(
            decision,
            entrySignal,
            strategyName,
            symbol,
            PERIOD_M5,
            reasonCode,
            StringFormat(
               "monitor-only %s intent: close=%.5f trigger=%.5f SL=%.5f TP=%.5f (%.1fR) "
               "sweep=%.5f buf=%.0fpts M15=%s",
               entrySignal == SIGNAL_ENTER_LONG_INTENT ? "long" : "short",
               entryPrice, m_reclaimLevel, stopLoss, takeProfit, takeProfitR,
               m_sweepExtreme, stopBufferPoints,
               m_isBullish ? "BULLISH" : "BEARISH"),
            now,
            stopLoss,
            takeProfit,
            1.0
         );
         SetSuggestedEntry(decision, entryPrice);
         AppendReasonCode(decision, reasonCode);
         SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
            minHoldSeconds, spreadStatus, volumeStatus);
         return;
      }

      // Fallback — should not be reached in normal operation
      SetWaitDecision(decision, "NYM15SR: unexpected internal state");
      PopulateStrategyDecision(decision, strategyName, symbol, timeframe,
         "NYM15SR_WAIT", now);
      SetDecisionContext(decision, symbolClass, sessionTag, nyTime, hasNYTime,
         minHoldSeconds, spreadStatus, volumeStatus);
   }
};

#endif

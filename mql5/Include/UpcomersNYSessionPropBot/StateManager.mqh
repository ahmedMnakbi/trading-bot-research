#ifndef UPCOMERS_NY_SESSION_PROP_BOT_STATE_MANAGER_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_STATE_MANAGER_MQH

#include "Config.mqh"
#include "StrategyBase.mqh"

class CStateManager
{
private:
   datetime m_startedAt;
   datetime m_futureOpenTime;
   bool m_hasFutureOpenTime;
   int m_ticksObserved;
   int m_timerEventsObserved;
   datetime m_lastEvaluationAt;
   datetime m_lastClosedBarEvaluatedAt;
   int m_monitorEvaluationsAllowed;
   int m_monitorEvaluationsThrottled;

public:
   void Init()
   {
      m_startedAt = TimeCurrent();
      m_futureOpenTime = 0;
      m_hasFutureOpenTime = false;
      m_ticksObserved = 0;
      m_timerEventsObserved = 0;
      m_lastEvaluationAt = 0;
      m_lastClosedBarEvaluatedAt = 0;
      m_monitorEvaluationsAllowed = 0;
      m_monitorEvaluationsThrottled = 0;
   }

   void CountTick()
   {
      m_ticksObserved++;
   }

   void CountTimer()
   {
      m_timerEventsObserved++;
   }

   int TicksObserved() const
   {
      return m_ticksObserved;
   }

   int TimerEventsObserved() const
   {
      return m_timerEventsObserved;
   }

   datetime StartedAt() const
   {
      return m_startedAt;
   }

   bool GetLatestClosedBarTime(
      const string symbol,
      const ENUM_TIMEFRAMES timeframe,
      datetime &closedBarTime,
      string &reason
   )
   {
      closedBarTime = 0;
      datetime closedTimes[];
      ArraySetAsSeries(closedTimes, true);
      int copied = CopyTime(symbol, timeframe, UPCOMERS_CLOSED_BAR_SHIFT, 1, closedTimes);
      if(copied < 1 || closedTimes[0] <= 0)
      {
         reason = "THROTTLE_WAIT_CLOSED_BAR: latest closed bar is unavailable";
         return false;
      }
      closedBarTime = closedTimes[0];
      reason = StringFormat(
         "latest closed bar time=%s shift=%d",
         TimeToString(closedBarTime, TIME_DATE | TIME_SECONDS),
         UPCOMERS_CLOSED_BAR_SHIFT
      );
      return true;
   }

   bool ShouldEvaluateMonitorEvent(
      const string eventName,
      const string symbol,
      const ENUM_TIMEFRAMES timeframe,
      const SUpcomersConfig &config,
      datetime &closedBarTime,
      string &reason
   )
   {
      datetime now = TimeCurrent();
      if(m_lastEvaluationAt > 0 && (now - m_lastEvaluationAt) < config.MinEvaluationSeconds)
      {
         m_monitorEvaluationsThrottled++;
         reason = StringFormat(
            "THROTTLE_MIN_SECONDS: skipped %s elapsed=%d required=%d",
            eventName,
            (int)(now - m_lastEvaluationAt),
            config.MinEvaluationSeconds
         );
         return false;
      }

      if(config.EvaluationMode == EVALUATION_TIMER && eventName != "OnTimer")
      {
         m_monitorEvaluationsThrottled++;
         reason = "THROTTLE_TIMER_MODE: OnTick skipped because EvaluationMode=Timer";
         return false;
      }

      if(config.EvaluationMode == EVALUATION_ON_NEW_CLOSED_BAR)
      {
         string barReason = "";
         if(!GetLatestClosedBarTime(symbol, timeframe, closedBarTime, barReason))
         {
            m_monitorEvaluationsThrottled++;
            reason = barReason;
            return false;
         }
         if(closedBarTime == m_lastClosedBarEvaluatedAt)
         {
            m_monitorEvaluationsThrottled++;
            reason = StringFormat(
               "THROTTLE_ON_NEW_CLOSED_BAR: closed bar %s already evaluated",
               TimeToString(closedBarTime, TIME_DATE | TIME_SECONDS)
            );
            return false;
         }
         reason = "THROTTLE_PASS_ON_NEW_CLOSED_BAR: " + barReason;
         return true;
      }

      closedBarTime = 0;
      reason = "THROTTLE_PASS_TIMER_MODE";
      return true;
   }

   void MarkMonitorEvaluation(const datetime closedBarTime)
   {
      m_lastEvaluationAt = TimeCurrent();
      if(closedBarTime > 0)
         m_lastClosedBarEvaluatedAt = closedBarTime;
      m_monitorEvaluationsAllowed++;
   }

   int MonitorEvaluationsAllowed() const
   {
      return m_monitorEvaluationsAllowed;
   }

   int MonitorEvaluationsThrottled() const
   {
      return m_monitorEvaluationsThrottled;
   }

   void SetFutureOpenTimeStub(const datetime openedAt)
   {
      m_futureOpenTime = openedAt;
      m_hasFutureOpenTime = true;
   }

   bool CanCloseAfterMinHold(
      const int minHoldSeconds,
      const bool emergencyHardStopRiskReduction,
      string &reason
   )
   {
      if(emergencyHardStopRiskReduction)
      {
         reason = "minimum hold guard bypassed only for emergency hard-stop risk reduction";
         return true;
      }
      if(!m_hasFutureOpenTime)
      {
         reason = "minimum hold guard has no future open position timestamp";
         return true;
      }
      int heldSeconds = (int)(TimeCurrent() - m_futureOpenTime);
      if(heldSeconds < minHoldSeconds)
      {
         reason = StringFormat("MinHoldSeconds guard blocks close: held=%d required=%d", heldSeconds, minHoldSeconds);
         return false;
      }
      reason = "minimum hold guard passed";
      return true;
   }
};

#endif

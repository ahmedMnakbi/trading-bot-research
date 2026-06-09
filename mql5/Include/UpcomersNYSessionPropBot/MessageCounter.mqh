#ifndef UPCOMERS_NY_SESSION_PROP_BOT_MESSAGE_COUNTER_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_MESSAGE_COUNTER_MQH

#include "Config.mqh"
#include "StrategyBase.mqh"

class CMessageCounter
{
private:
   int m_monitorEvaluations;
   int m_tradeIntentEvents;
   int m_refusedTradeActions;
   int m_actualServerMessages;
   int m_propDayKey;

public:
   void Reset()
   {
      m_monitorEvaluations = 0;
      m_tradeIntentEvents = 0;
      m_refusedTradeActions = 0;
      m_actualServerMessages = 0;
      m_propDayKey = 0;
   }

   void ResetForNewPropDay(const int propDayKey)
   {
      if(m_propDayKey == propDayKey)
         return;
      m_propDayKey = propDayKey;
      m_tradeIntentEvents = 0;
      m_refusedTradeActions = 0;
      m_actualServerMessages = 0;
   }

   bool IsActionableIntent(const ENUM_UPCOMERS_SIGNAL signal) const
   {
      return signal == SIGNAL_ENTER_LONG_INTENT ||
             signal == SIGNAL_ENTER_SHORT_INTENT ||
             signal == SIGNAL_EXIT_INTENT;
   }

   void CountMonitorEvaluation()
   {
      m_monitorEvaluations++;
   }

   void CountDecision()
   {
      CountMonitorEvaluation();
   }

   void RecordTradeIntentEvent()
   {
      m_tradeIntentEvents++;
   }

   void RecordRefusedTradeAction()
   {
      m_refusedTradeActions++;
   }

   void RecordActualServerMessage()
   {
      m_actualServerMessages++;
   }

   void RecordTradeActionRequest()
   {
      RecordRefusedTradeAction();
   }

   void RecordServerMessageRequest()
   {
      RecordActualServerMessage();
   }

   bool CheckTradeActionLimit(const SUpcomersConfig &config, string &reason)
   {
      if(m_tradeIntentEvents > config.MaxTradesPerDay)
      {
         reason = "MaxTradesPerDay guard reached for monitor-only trade intent events";
         return false;
      }
      reason = StringFormat(
         "trade intent counter guard passed intents=%d refused=%d monitor_evaluations=%d",
         m_tradeIntentEvents,
         m_refusedTradeActions,
         m_monitorEvaluations
      );
      return true;
   }

   bool CanSendServerMessage(const SUpcomersConfig &config, string &reason)
   {
      if(m_actualServerMessages > config.MaxServerMessagesPerDay)
      {
         reason = "MaxServerMessagesPerDay guard reached";
         return false;
      }
      reason = StringFormat(
         "actual server message guard passed actual_server_messages=%d",
         m_actualServerMessages
      );
      return true;
   }

   int DecisionMessages() const
   {
      return m_monitorEvaluations;
   }

   int MonitorEvaluations() const
   {
      return m_monitorEvaluations;
   }

   int TradeIntentEvents() const
   {
      return m_tradeIntentEvents;
   }

   int RefusedTradeActions() const
   {
      return m_refusedTradeActions;
   }

   int ServerMessages() const
   {
      return m_actualServerMessages;
   }

   int ActualServerMessages() const
   {
      return m_actualServerMessages;
   }

   int TradeActionRequests() const
   {
      return m_refusedTradeActions;
   }
};

#endif

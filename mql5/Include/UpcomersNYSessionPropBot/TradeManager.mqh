#ifndef UPCOMERS_NY_SESSION_PROP_BOT_TRADE_MANAGER_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_TRADE_MANAGER_MQH

#include "StrategyBase.mqh"
#include "Config.mqh"
#include "MessageCounter.mqh"
#include "StateManager.mqh"

enum ENUM_UPCOMERS_TRADE_REQUEST_RESULT
{
   TRADE_REQUEST_REJECTED = 0,
   TRADE_REQUEST_REFUSED = 1
};

class CMonitorTradeManager
{
public:
   bool RefuseExecution(
      const SStrategyDecision &decision,
      const SUpcomersConfig &config,
      CMessageCounter &messageCounter,
      CStateManager &state,
      string &reason
   )
   {
      string guardReason = "";
      if(!messageCounter.IsActionableIntent(decision.Signal))
      {
         reason = StringFormat(
            "NO_ACTION Phase 10.1 monitor TradeManager for non-actionable signal %s: "
            "WAIT/skip/setup evaluations do not count as trade attempts or server messages",
            SignalToString(decision.Signal)
         );
         return false;
      }
      messageCounter.RecordTradeIntentEvent();
      messageCounter.RecordRefusedTradeAction();
      if(!messageCounter.CheckTradeActionLimit(config, guardReason))
      {
         reason = "REJECTED by no-trade TradeManager: " + guardReason;
         return false;
      }
      if(!messageCounter.CanSendServerMessage(config, guardReason))
      {
         reason = "REJECTED by no-trade TradeManager: " + guardReason;
         return false;
      }
      if(!state.CanCloseAfterMinHold(config.MinHoldSeconds, false, guardReason))
      {
         reason = "REJECTED by no-trade TradeManager: " + guardReason;
         return false;
      }
      reason = StringFormat(
         "REFUSED Phase 9 no-trade TradeManager for intent signal %s: %s",
         SignalToString(decision.Signal),
         decision.Reason
      );
      return false;
   }
};

#endif

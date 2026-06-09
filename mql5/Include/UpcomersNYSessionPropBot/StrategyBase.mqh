#ifndef UPCOMERS_NY_SESSION_PROP_BOT_STRATEGY_BASE_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_STRATEGY_BASE_MQH

enum ENUM_UPCOMERS_SIGNAL
{
   SIGNAL_WAIT = 0,
   SIGNAL_SETUP_FORMING = 1,
   SIGNAL_ENTER_LONG_INTENT = 2,
   SIGNAL_ENTER_SHORT_INTENT = 3,
   SIGNAL_EXIT_INTENT = 4,
   SIGNAL_SKIP_SESSION = 5,
   SIGNAL_SKIP_SPREAD = 6,
   SIGNAL_SKIP_NEWS = 7,
   SIGNAL_SKIP_DATA = 8,
   SIGNAL_SESSION_CLOSE = 9
};

const int UPCOMERS_CLOSED_BAR_SHIFT = 1;

struct SStrategyDecision
{
   ENUM_UPCOMERS_SIGNAL Signal;
   string StrategyName;
   string SymbolName;
   string SymbolClass;
   ENUM_TIMEFRAMES Timeframe;
   string Direction;
   string ReasonCode;
   string ReasonCodes;
   datetime Timestamp;
   datetime ServerTimestamp;
   datetime NewYorkTimestamp;
   bool HasNewYorkTimestamp;
   string SessionTag;
   double SuggestedEntry;
   double SuggestedStopLoss;
   double SuggestedTakeProfit;
   datetime MinHoldUntil;
   string SpreadFilterStatus;
   string VolumeTypeUsed;
   string MonitorOnlyNote;
   double QualityScore;
   bool HasSuggestedEntry;
   bool HasStopLoss;
   bool HasTakeProfit;
   string Reason;
};

string TimeframeToDecisionText(const ENUM_TIMEFRAMES timeframe)
{
   return EnumToString(timeframe);
}

void ResetStrategyDecision(SStrategyDecision &decision)
{
   decision.Signal = SIGNAL_WAIT;
   decision.StrategyName = "";
   decision.SymbolName = "";
   decision.SymbolClass = "UNKNOWN";
   decision.Timeframe = PERIOD_CURRENT;
   decision.Direction = "NONE";
   decision.ReasonCode = "WAIT";
   decision.ReasonCodes = "WAIT";
   decision.Timestamp = TimeCurrent();
   decision.ServerTimestamp = decision.Timestamp;
   decision.NewYorkTimestamp = 0;
   decision.HasNewYorkTimestamp = false;
   decision.SessionTag = "SESSION_UNVERIFIED";
   decision.SuggestedEntry = 0.0;
   decision.SuggestedStopLoss = 0.0;
   decision.SuggestedTakeProfit = 0.0;
   decision.MinHoldUntil = 0;
   decision.SpreadFilterStatus = "SPREAD_CHECK_PENDING";
   decision.VolumeTypeUsed = "VOLUME_NOT_APPLICABLE";
   decision.MonitorOnlyNote = "MONITOR_ONLY_NO_ORDER_PLACEMENT";
   decision.QualityScore = 0.0;
   decision.HasSuggestedEntry = false;
   decision.HasStopLoss = false;
   decision.HasTakeProfit = false;
   decision.Reason = "waiting";
}

void PopulateStrategyDecision(
   SStrategyDecision &decision,
   const string strategyName,
   const string symbol,
   const ENUM_TIMEFRAMES timeframe,
   const string reasonCode,
   const datetime timestamp
)
{
   decision.StrategyName = strategyName;
   decision.SymbolName = symbol;
   decision.Timeframe = timeframe;
   decision.ReasonCode = reasonCode;
   decision.Timestamp = timestamp;
   decision.ServerTimestamp = timestamp;
}

void AppendReasonCode(SStrategyDecision &decision, const string reasonCode)
{
   if(StringLen(reasonCode) == 0)
      return;
   if(StringLen(decision.ReasonCodes) == 0 || decision.ReasonCodes == "WAIT")
      decision.ReasonCodes = reasonCode;
   else if(StringFind(decision.ReasonCodes, reasonCode) < 0)
      decision.ReasonCodes = decision.ReasonCodes + "|" + reasonCode;
}

void SetDecisionContext(
   SStrategyDecision &decision,
   const string symbolClass,
   const string sessionTag,
   const datetime newYorkTimestamp,
   const bool hasNewYorkTimestamp,
   const int minHoldSeconds,
   const string spreadFilterStatus,
   const string volumeTypeUsed = "VOLUME_NOT_APPLICABLE"
)
{
   decision.SymbolClass = symbolClass;
   decision.SessionTag = sessionTag;
   decision.NewYorkTimestamp = newYorkTimestamp;
   decision.HasNewYorkTimestamp = hasNewYorkTimestamp;
   decision.MinHoldUntil = decision.ServerTimestamp + minHoldSeconds;
   decision.SpreadFilterStatus = spreadFilterStatus;
   decision.VolumeTypeUsed = volumeTypeUsed;
   decision.MonitorOnlyNote = "MONITOR_ONLY_STRATEGY_INTENT_TRADEMANAGER_REFUSES_EXECUTION";
}

void SetSuggestedEntry(SStrategyDecision &decision, const double suggestedEntry)
{
   if(suggestedEntry <= 0.0)
      return;
   decision.SuggestedEntry = suggestedEntry;
   decision.HasSuggestedEntry = true;
}

void SetWaitDecision(SStrategyDecision &decision, const string reason)
{
   ResetStrategyDecision(decision);
   decision.Signal = SIGNAL_WAIT;
   decision.ReasonCode = "WAIT";
   decision.ReasonCodes = "WAIT";
   decision.Reason = reason;
}

void SetSkipDecision(
   SStrategyDecision &decision,
   const ENUM_UPCOMERS_SIGNAL signal,
   const string strategyName,
   const string symbol,
   const ENUM_TIMEFRAMES timeframe,
   const string reasonCode,
   const string reason,
   const datetime timestamp
)
{
   ResetStrategyDecision(decision);
   decision.Signal = signal;
   PopulateStrategyDecision(decision, strategyName, symbol, timeframe, reasonCode, timestamp);
   decision.ReasonCodes = reasonCode;
   decision.Reason = reason;
}

void SetSetupFormingDecision(SStrategyDecision &decision, const string reason)
{
   ResetStrategyDecision(decision);
   decision.Signal = SIGNAL_SETUP_FORMING;
   decision.ReasonCode = "SETUP_FORMING";
   decision.ReasonCodes = "SETUP_FORMING";
   decision.Reason = reason;
}

void SetSetupFormingDecision(
   SStrategyDecision &decision,
   const string strategyName,
   const string symbol,
   const ENUM_TIMEFRAMES timeframe,
   const string reasonCode,
   const string reason,
   const datetime timestamp,
   const double qualityScore = 0.0
)
{
   ResetStrategyDecision(decision);
   decision.Signal = SIGNAL_SETUP_FORMING;
   PopulateStrategyDecision(decision, strategyName, symbol, timeframe, reasonCode, timestamp);
   decision.ReasonCodes = reasonCode;
   decision.QualityScore = qualityScore;
   decision.Reason = reason;
}

void SetEntryIntentDecision(
   SStrategyDecision &decision,
   const ENUM_UPCOMERS_SIGNAL signal,
   const string strategyName,
   const string symbol,
   const ENUM_TIMEFRAMES timeframe,
   const string reasonCode,
   const string reason,
   const datetime timestamp,
   const double stopLoss,
   const double takeProfit,
   const double qualityScore
)
{
   ResetStrategyDecision(decision);
   if(stopLoss <= 0.0)
   {
      decision.Signal = SIGNAL_SKIP_DATA;
      PopulateStrategyDecision(decision, strategyName, symbol, timeframe, "SKIP_DATA_NO_STOP_LOSS", timestamp);
      decision.ReasonCodes = "SKIP_DATA_NO_STOP_LOSS";
      decision.Reason = "entry intent blocked because stop-loss could not be computed";
      return;
   }
   decision.Signal = signal;
   PopulateStrategyDecision(decision, strategyName, symbol, timeframe, reasonCode, timestamp);
   decision.ReasonCodes = reasonCode;
   decision.Direction = (signal == SIGNAL_ENTER_LONG_INTENT ? "LONG" : "SHORT");
   decision.SuggestedStopLoss = stopLoss;
   decision.SuggestedTakeProfit = takeProfit;
   decision.HasStopLoss = true;
   decision.HasTakeProfit = takeProfit > 0.0;
   decision.QualityScore = qualityScore;
   decision.Reason = reason;
}

bool EntryIntentHasRequiredStopLoss(const SStrategyDecision &decision)
{
   if(decision.Signal != SIGNAL_ENTER_LONG_INTENT && decision.Signal != SIGNAL_ENTER_SHORT_INTENT)
      return true;
   return decision.HasStopLoss && decision.SuggestedStopLoss > 0.0;
}

string SignalToString(const ENUM_UPCOMERS_SIGNAL signal)
{
   if(signal == SIGNAL_SETUP_FORMING)
      return "SETUP_FORMING";
   if(signal == SIGNAL_ENTER_LONG_INTENT)
      return "ENTER_LONG_INTENT";
   if(signal == SIGNAL_ENTER_SHORT_INTENT)
      return "ENTER_SHORT_INTENT";
   if(signal == SIGNAL_EXIT_INTENT)
      return "EXIT_INTENT";
   if(signal == SIGNAL_SKIP_SESSION)
      return "SKIP_SESSION";
   if(signal == SIGNAL_SKIP_SPREAD)
      return "SKIP_SPREAD";
   if(signal == SIGNAL_SKIP_NEWS)
      return "SKIP_NEWS";
   if(signal == SIGNAL_SKIP_DATA)
      return "SKIP_DATA";
   if(signal == SIGNAL_SESSION_CLOSE)
      return "SESSION_CLOSE";
   return "WAIT";
}

#endif

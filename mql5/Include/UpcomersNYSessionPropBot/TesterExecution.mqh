#ifndef UPCOMERS_NY_SESSION_PROP_BOT_TESTER_EXECUTION_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_TESTER_EXECUTION_MQH

#include "Config.mqh"
#include "Logger.mqh"
#include "MessageCounter.mqh"
#include "StateManager.mqh"
#include "StrategyBase.mqh"

class CTesterExecutionManager
{
private:
   string m_lastAttemptKey;
   bool m_hasLastAttemptKey;
   int m_testerEntryIntentsReceived;
   int m_testerOrdersAttempted;
   int m_testerOrdersSentSuccess;
   int m_testerOrdersRejected;
   int m_testerOrdersSkippedByGate;
   int m_gateValidateConfigFailures;
   int m_gateMqlTesterFailures;
   int m_gateStrategyModeFailures;
   int m_gateEnableTradingFailures;
   int m_gateEnableTrialFailures;
   int m_gatePropChallengeFailures;
   int m_gateAccountProgramFailures;
   int m_gateAccountStageFailures;
   int m_gateAllowedSymbolsFailures;
   int m_gateStopLossRequiredFailures;
   int m_gateMinHoldFailures;
   int m_gateSpreadFilterFailures;
   int m_gateSpreadFailures;
   int m_gatePositionTotalFailures;
   int m_gatePositionSymbolFailures;
   int m_gateTradeAttemptsFailures;
   int m_gateServerMessagesFailures;
   int m_gateOneAttemptFailures;
   int m_gateBidAskFailures;
   int m_gateSymbolMetadataFailures;
   int m_gateSltpFailures;
   int m_gateLotSizeFailures;
   string m_lastGateFailure;

   void AppendCount(string &summary, const string name, const int value) const
   {
      if(StringLen(summary) > 0)
         summary += "|";
      summary += StringFormat("%s:%d", name, value);
   }

   void RecordGateFailure(const string gateName)
   {
      m_testerOrdersSkippedByGate++;
      m_lastGateFailure = gateName;

      if(gateName == "ValidateStrategyTesterExecutionConfig")
         m_gateValidateConfigFailures++;
      else if(gateName == "MQL_TESTER")
         m_gateMqlTesterFailures++;
      else if(gateName == "StrategyTesterExecutionMode")
         m_gateStrategyModeFailures++;
      else if(gateName == "EnableTradingInputFalse")
         m_gateEnableTradingFailures++;
      else if(gateName == "EnableTrialExecutionFalse")
         m_gateEnableTrialFailures++;
      else if(gateName == "EnablePropChallengeModeFalse")
         m_gatePropChallengeFailures++;
      else if(gateName == "AccountProgramTrialRiskFree")
         m_gateAccountProgramFailures++;
      else if(gateName == "AccountStageMonitorOnly")
         m_gateAccountStageFailures++;
      else if(gateName == "AllowedSymbols")
         m_gateAllowedSymbolsFailures++;
      else if(gateName == "StopLossRequired")
         m_gateStopLossRequiredFailures++;
      else if(gateName == "MinHoldSeconds")
         m_gateMinHoldFailures++;
      else if(gateName == "UseSpreadFilter")
         m_gateSpreadFilterFailures++;
      else if(gateName == "Spread")
         m_gateSpreadFailures++;
      else if(gateName == "PositionCapsTotal")
         m_gatePositionTotalFailures++;
      else if(gateName == "PositionCapsSymbol")
         m_gatePositionSymbolFailures++;
      else if(gateName == "TradeAttemptsToday")
         m_gateTradeAttemptsFailures++;
      else if(gateName == "ServerMessagesToday")
         m_gateServerMessagesFailures++;
      else if(gateName == "OneAttemptPerSignal")
         m_gateOneAttemptFailures++;
      else if(gateName == "BidAsk")
         m_gateBidAskFailures++;
      else if(gateName == "SymbolMetadata")
         m_gateSymbolMetadataFailures++;
      else if(gateName == "SLTP")
         m_gateSltpFailures++;
      else if(gateName == "LotSize")
         m_gateLotSizeFailures++;
   }

   void LogGateFailure(
      CUpcomersLogger &logger,
      const string gateName,
      const string detail,
      string &reason
   )
   {
      RecordGateFailure(gateName);
      logger.Warn(
         "TesterExecution",
         StringFormat("TESTER_GATE_FAIL_%s detail=%s", gateName, detail)
      );
      reason = "TESTER_EXECUTION_DENIED gate=" + gateName + " detail=" + detail;
   }

   bool LogGate(
      CUpcomersLogger &logger,
      const string gateName,
      const bool passed,
      const string detail,
      string &reason
   )
   {
      string message = StringFormat("TESTER_EXECUTION_GATE %s=%s %s", gateName, BoolToText(passed), detail);
      if(passed)
         logger.Info("TesterExecution", message);
      else
      {
         logger.Warn("TesterExecution", message);
         LogGateFailure(logger, gateName, detail, reason);
      }
      return passed;
   }

   string BuildAttemptKey(const SStrategyDecision &decision, const string symbol) const
   {
      return StringFormat(
         "%s|%s|%s|%s|%.5f|%.5f",
         symbol,
         SignalToString(decision.Signal),
         decision.StrategyName,
         TimeToString(decision.ServerTimestamp, TIME_DATE | TIME_SECONDS),
         decision.SuggestedStopLoss,
         decision.SuggestedTakeProfit
      );
   }

   int CountOpenPositionsForSymbol(const string symbol) const
   {
      int count = 0;
      for(int index = PositionsTotal() - 1; index >= 0; index--)
      {
         string positionSymbol = PositionGetSymbol(index);
         if(positionSymbol == symbol)
            count++;
      }
      return count;
   }

   bool ReadPositiveSymbolDouble(
      const string symbol,
      const ENUM_SYMBOL_INFO_DOUBLE propertyId,
      const string propertyName,
      double &value,
      string &reason
   ) const
   {
      value = 0.0;
      if(!SymbolInfoDouble(symbol, propertyId, value) || value <= 0.0)
      {
         reason = propertyName + " unavailable or non-positive";
         return false;
      }
      reason = StringFormat("%s=%.8f", propertyName, value);
      return true;
   }

   bool ReadPositivePriceMetadata(
      const string symbol,
      long &digits,
      double &point,
      string &reason
   ) const
   {
      digits = 0;
      point = 0.0;
      if(!SymbolInfoInteger(symbol, SYMBOL_DIGITS, digits) || digits < 0)
      {
         reason = "SYMBOL_DIGITS unavailable or negative";
         return false;
      }
      if(!SymbolInfoDouble(symbol, SYMBOL_POINT, point) || point <= 0.0)
      {
         reason = "SYMBOL_POINT unavailable or non-positive";
         return false;
      }
      reason = StringFormat("SYMBOL_DIGITS=%d SYMBOL_POINT=%.10f", (int)digits, point);
      return true;
   }

   int VolumeDigitsFromStep(const double volumeStep) const
   {
      if(volumeStep <= 0.0)
         return 2;
      int digits = 0;
      double scaled = volumeStep;
      while(digits < 8 && MathAbs(scaled - MathRound(scaled)) > 0.000000001)
      {
         scaled *= 10.0;
         digits++;
      }
      return digits;
   }

   double NormalizeVolumeToMinStep(
      const double rawVolume,
      const double minVolume,
      const double volumeStep
   ) const
   {
      if(volumeStep <= 0.0)
         return rawVolume;

      double normalized = MathFloor((rawVolume / volumeStep) + 0.000000001) * volumeStep;
      if(normalized < minVolume)
         normalized = MathCeil((minVolume / volumeStep) - 0.000000001) * volumeStep;
      return NormalizeDouble(normalized, VolumeDigitsFromStep(volumeStep));
   }

   ENUM_ORDER_TYPE_FILLING ResolveTesterFillingMode(
      const string symbol,
      long &symbolFillingMode,
      string &reason
   ) const
   {
      symbolFillingMode = -1;
      if(!SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE, symbolFillingMode))
      {
         reason = "SYMBOL_FILLING_MODE unavailable; fallback ORDER_FILLING_RETURN";
         return ORDER_FILLING_RETURN;
      }

      if((symbolFillingMode & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
      {
         reason = StringFormat(
            "SYMBOL_FILLING_MODE=%d supports SYMBOL_FILLING_IOC; request.type_filling=ORDER_FILLING_IOC",
            (int)symbolFillingMode
         );
         return ORDER_FILLING_IOC;
      }
      if((symbolFillingMode & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
      {
         reason = StringFormat(
            "SYMBOL_FILLING_MODE=%d supports SYMBOL_FILLING_FOK; request.type_filling=ORDER_FILLING_FOK",
            (int)symbolFillingMode
         );
         return ORDER_FILLING_FOK;
      }

      reason = StringFormat(
         "SYMBOL_FILLING_MODE=%d has no IOC/FOK flag; fallback request.type_filling=ORDER_FILLING_RETURN",
         (int)symbolFillingMode
      );
      return ORDER_FILLING_RETURN;
   }

   bool ResolveMinimumTesterLot(
      const string symbol,
      const SUpcomersConfig &config,
      const double entryPrice,
      const double stopLoss,
      double &volume,
      string &reason
   ) const
   {
      double minVolume = 0.0;
      double volumeStep = 0.0;
      double tickSize = 0.0;
      double tickValue = 0.0;
      string detail = "";
      if(!ReadPositiveSymbolDouble(symbol, SYMBOL_VOLUME_MIN, "SYMBOL_VOLUME_MIN", minVolume, detail))
      {
         reason = detail;
         return false;
      }
      if(!ReadPositiveSymbolDouble(symbol, SYMBOL_VOLUME_STEP, "SYMBOL_VOLUME_STEP", volumeStep, detail))
      {
         reason = detail;
         return false;
      }
      if(!ReadPositiveSymbolDouble(symbol, SYMBOL_TRADE_TICK_SIZE, "SYMBOL_TRADE_TICK_SIZE", tickSize, detail))
      {
         reason = detail;
         return false;
      }
      if(!ReadPositiveSymbolDouble(symbol, SYMBOL_TRADE_TICK_VALUE, "SYMBOL_TRADE_TICK_VALUE", tickValue, detail))
      {
         reason = detail;
         return false;
      }

      double balance = AccountInfoDouble(ACCOUNT_BALANCE);
      if(balance <= 0.0)
      {
         reason = "ACCOUNT_BALANCE unavailable or non-positive";
         return false;
      }

      double priceRisk = MathAbs(entryPrice - stopLoss);
      if(priceRisk <= 0.0)
      {
         reason = "entry and stop-loss distance is non-positive";
         return false;
      }

      double lossPerLot = (priceRisk / tickSize) * tickValue;
      if(lossPerLot <= 0.0)
      {
         reason = "computed loss per lot is non-positive";
         return false;
      }

      double riskBudget = balance * (config.RiskPerTradePct / 100.0);
      double riskBasedLot = riskBudget / lossPerLot;
      if(riskBasedLot < minVolume)
      {
         reason = StringFormat(
            "tester minimum lot %.4f exceeds conservative risk-based lot %.4f; simulated order not sent",
            minVolume,
            riskBasedLot
         );
         return false;
      }

      double rawVolume = minVolume;
      volume = NormalizeVolumeToMinStep(rawVolume, minVolume, volumeStep);
      if(volume < minVolume || volume <= 0.0)
      {
         reason = StringFormat(
            "VOLUME_NORMALIZED_TO_MIN_STEP failed raw_volume=%.8f normalized=%.8f min=%.8f step=%.8f",
            rawVolume,
            volume,
            minVolume,
            volumeStep
         );
         return false;
      }
      reason = StringFormat(
         "VOLUME_NORMALIZED_TO_MIN_STEP tester minimum lot selected raw_volume=%.8f volume=%.8f min=%.8f volume_step=%.8f risk_based_lot=%.8f risk_pct=%.2f",
         rawVolume,
         volume,
         minVolume,
         volumeStep,
         riskBasedLot,
         config.RiskPerTradePct
      );
      return true;
   }

   bool ValidateStopAndTakeProfit(
      const string symbol,
      const SStrategyDecision &decision,
      const double entryPrice,
      string &reason
   ) const
   {
      if(!decision.HasStopLoss || !decision.HasTakeProfit ||
         decision.SuggestedStopLoss <= 0.0 || decision.SuggestedTakeProfit <= 0.0)
      {
         reason = "SL/TP required: tester entry intent must include both stop-loss and take-profit";
         return false;
      }
      if(decision.Signal == SIGNAL_ENTER_LONG_INTENT)
      {
         if(decision.SuggestedStopLoss >= entryPrice || decision.SuggestedTakeProfit <= entryPrice)
         {
            reason = "invalid LONG tester SL/TP geometry";
            return false;
         }
      }
      else if(decision.Signal == SIGNAL_ENTER_SHORT_INTENT)
      {
         if(decision.SuggestedStopLoss <= entryPrice || decision.SuggestedTakeProfit >= entryPrice)
         {
            reason = "invalid SHORT tester SL/TP geometry";
            return false;
         }
      }
      else
      {
         reason = "not an entry intent";
         return false;
      }

      long stopsLevelPoints = 0;
      bool hasStopsLevel = SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL, stopsLevelPoints);
      if(hasStopsLevel && stopsLevelPoints > 0)
      {
         double point = 0.0;
         if(!SymbolInfoDouble(symbol, SYMBOL_POINT, point) || point <= 0.0)
         {
            reason = "SYMBOL_POINT unavailable while SYMBOL_TRADE_STOPS_LEVEL is positive";
            return false;
         }
         double minimumDistance = (double)stopsLevelPoints * point;
         double stopDistance = MathAbs(entryPrice - decision.SuggestedStopLoss);
         double takeProfitDistance = MathAbs(entryPrice - decision.SuggestedTakeProfit);
         if(stopDistance < minimumDistance || takeProfitDistance < minimumDistance)
         {
            reason = StringFormat(
               "STOP_LEVEL_CONSTRAINT failed: stops_level_points=%d min_distance=%.8f sl_distance=%.8f tp_distance=%.8f",
               (int)stopsLevelPoints,
               minimumDistance,
               stopDistance,
               takeProfitDistance
            );
            return false;
         }
         reason = StringFormat(
            "tester SL/TP geometry and STOP_LEVEL_CONSTRAINT validated stops_level_points=%d",
            (int)stopsLevelPoints
         );
         return true;
      }
      if(!hasStopsLevel)
      {
         reason = "tester SL/TP geometry validated; SYMBOL_TRADE_STOPS_LEVEL unavailable";
         return true;
      }
      reason = "tester SL/TP geometry validated";
      return true;
   }

   bool ValidateRequestGeometry(
      const string symbol,
      const ENUM_UPCOMERS_SIGNAL signal,
      const double entryPrice,
      const double stopLoss,
      const double takeProfit,
      string &reason
   ) const
   {
      if(stopLoss <= 0.0 || takeProfit <= 0.0)
      {
         reason = "normalized SL/TP required and must be positive";
         return false;
      }
      if(signal == SIGNAL_ENTER_LONG_INTENT)
      {
         if(stopLoss >= entryPrice || takeProfit <= entryPrice)
         {
            reason = "normalized LONG request has invalid SL/TP geometry";
            return false;
         }
      }
      else if(signal == SIGNAL_ENTER_SHORT_INTENT)
      {
         if(stopLoss <= entryPrice || takeProfit >= entryPrice)
         {
            reason = "normalized SHORT request has invalid SL/TP geometry";
            return false;
         }
      }
      else
      {
         reason = "normalized request is not an entry intent";
         return false;
      }

      long stopsLevelPoints = 0;
      bool hasStopsLevel = SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL, stopsLevelPoints);
      if(hasStopsLevel && stopsLevelPoints > 0)
      {
         double point = 0.0;
         if(!SymbolInfoDouble(symbol, SYMBOL_POINT, point) || point <= 0.0)
         {
            reason = "SYMBOL_POINT unavailable while validating normalized STOP_LEVEL_CONSTRAINT";
            return false;
         }
         double minimumDistance = (double)stopsLevelPoints * point;
         double stopDistance = MathAbs(entryPrice - stopLoss);
         double takeProfitDistance = MathAbs(entryPrice - takeProfit);
         if(stopDistance < minimumDistance || takeProfitDistance < minimumDistance)
         {
            reason = StringFormat(
               "normalized STOP_LEVEL_CONSTRAINT failed: stops_level_points=%d min_distance=%.8f sl_distance=%.8f tp_distance=%.8f",
               (int)stopsLevelPoints,
               minimumDistance,
               stopDistance,
               takeProfitDistance
            );
            return false;
         }
      }
      reason = "normalized price/SL/TP request geometry validated";
      return true;
   }

   void ReadOrderSymbolDiagnostics(
      const string symbol,
      long &symbolFillingMode,
      long &symbolTradeMode,
      long &stopsLevelPoints,
      long &freezeLevelPoints,
      double &volumeMin,
      double &volumeStep,
      double &bid,
      double &ask,
      double &point,
      long &digits
   ) const
   {
      symbolFillingMode = -1;
      symbolTradeMode = -1;
      stopsLevelPoints = -1;
      freezeLevelPoints = -1;
      volumeMin = -1.0;
      volumeStep = -1.0;
      bid = -1.0;
      ask = -1.0;
      point = -1.0;
      digits = -1;
      SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE, symbolFillingMode);
      SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE, symbolTradeMode);
      SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL, stopsLevelPoints);
      SymbolInfoInteger(symbol, SYMBOL_TRADE_FREEZE_LEVEL, freezeLevelPoints);
      SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN, volumeMin);
      SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP, volumeStep);
      SymbolInfoDouble(symbol, SYMBOL_BID, bid);
      SymbolInfoDouble(symbol, SYMBOL_ASK, ask);
      SymbolInfoDouble(symbol, SYMBOL_POINT, point);
      SymbolInfoInteger(symbol, SYMBOL_DIGITS, digits);
   }

   string TesterOrderRequestDiagnostics(
      const MqlTradeRequest &request,
      const long symbolFillingMode,
      const long symbolTradeMode,
      const long stopsLevelPoints,
      const long freezeLevelPoints,
      const double volumeMin,
      const double volumeStep,
      const double bid,
      const double ask,
      const double point,
      const long digits
   ) const
   {
      return StringFormat(
         "request.action=%s request.type=%s request.symbol=%s request.volume=%.8f request.price=%.8f request.sl=%.8f request.tp=%.8f request.deviation=%d request.type_filling=%s SYMBOL_FILLING_MODE=%d SYMBOL_TRADE_MODE=%d SYMBOL_TRADE_STOPS_LEVEL=%d SYMBOL_TRADE_FREEZE_LEVEL=%d SYMBOL_VOLUME_MIN=%.8f SYMBOL_VOLUME_STEP=%.8f bid=%.8f ask=%.8f point=%.10f digits=%d",
         EnumToString(request.action),
         EnumToString(request.type),
         request.symbol,
         request.volume,
         request.price,
         request.sl,
         request.tp,
         (int)request.deviation,
         EnumToString(request.type_filling),
         (int)symbolFillingMode,
         (int)symbolTradeMode,
         (int)stopsLevelPoints,
         (int)freezeLevelPoints,
         volumeMin,
         volumeStep,
         bid,
         ask,
         point,
         (int)digits
      );
   }

public:
   void Reset()
   {
      m_lastAttemptKey = "";
      m_hasLastAttemptKey = false;
      m_testerEntryIntentsReceived = 0;
      m_testerOrdersAttempted = 0;
      m_testerOrdersSentSuccess = 0;
      m_testerOrdersRejected = 0;
      m_testerOrdersSkippedByGate = 0;
      m_gateValidateConfigFailures = 0;
      m_gateMqlTesterFailures = 0;
      m_gateStrategyModeFailures = 0;
      m_gateEnableTradingFailures = 0;
      m_gateEnableTrialFailures = 0;
      m_gatePropChallengeFailures = 0;
      m_gateAccountProgramFailures = 0;
      m_gateAccountStageFailures = 0;
      m_gateAllowedSymbolsFailures = 0;
      m_gateStopLossRequiredFailures = 0;
      m_gateMinHoldFailures = 0;
      m_gateSpreadFilterFailures = 0;
      m_gateSpreadFailures = 0;
      m_gatePositionTotalFailures = 0;
      m_gatePositionSymbolFailures = 0;
      m_gateTradeAttemptsFailures = 0;
      m_gateServerMessagesFailures = 0;
      m_gateOneAttemptFailures = 0;
      m_gateBidAskFailures = 0;
      m_gateSymbolMetadataFailures = 0;
      m_gateSltpFailures = 0;
      m_gateLotSizeFailures = 0;
      m_lastGateFailure = "none";
   }

   int TesterOrdersAttempted() const
   {
      return m_testerOrdersAttempted;
   }

   string GateFailureSummary() const
   {
      string summary = "";
      AppendCount(summary, "ValidateStrategyTesterExecutionConfig", m_gateValidateConfigFailures);
      AppendCount(summary, "MQL_TESTER", m_gateMqlTesterFailures);
      AppendCount(summary, "StrategyTesterExecutionMode", m_gateStrategyModeFailures);
      AppendCount(summary, "EnableTradingInputFalse", m_gateEnableTradingFailures);
      AppendCount(summary, "EnableTrialExecutionFalse", m_gateEnableTrialFailures);
      AppendCount(summary, "EnablePropChallengeModeFalse", m_gatePropChallengeFailures);
      AppendCount(summary, "AccountProgramTrialRiskFree", m_gateAccountProgramFailures);
      AppendCount(summary, "AccountStageMonitorOnly", m_gateAccountStageFailures);
      AppendCount(summary, "AllowedSymbols", m_gateAllowedSymbolsFailures);
      AppendCount(summary, "StopLossRequired", m_gateStopLossRequiredFailures);
      AppendCount(summary, "MinHoldSeconds", m_gateMinHoldFailures);
      AppendCount(summary, "UseSpreadFilter", m_gateSpreadFilterFailures);
      AppendCount(summary, "Spread", m_gateSpreadFailures);
      AppendCount(summary, "PositionCapsTotal", m_gatePositionTotalFailures);
      AppendCount(summary, "PositionCapsSymbol", m_gatePositionSymbolFailures);
      AppendCount(summary, "TradeAttemptsToday", m_gateTradeAttemptsFailures);
      AppendCount(summary, "ServerMessagesToday", m_gateServerMessagesFailures);
      AppendCount(summary, "OneAttemptPerSignal", m_gateOneAttemptFailures);
      AppendCount(summary, "BidAsk", m_gateBidAskFailures);
      AppendCount(summary, "SymbolMetadata", m_gateSymbolMetadataFailures);
      AppendCount(summary, "SLTP", m_gateSltpFailures);
      AppendCount(summary, "LotSize", m_gateLotSizeFailures);
      return summary;
   }

   string Summary(const string eventName) const
   {
      return StringFormat(
         "TESTER_EXECUTION_SUMMARY tester_entry_intents_received=%d tester_orders_attempted=%d tester_orders_sent_success=%d tester_orders_rejected=%d tester_orders_skipped_by_gate=%d top_tester_gate_failures=%s last_tester_gate_failure=%s event=%s",
         m_testerEntryIntentsReceived,
         m_testerOrdersAttempted,
         m_testerOrdersSentSuccess,
         m_testerOrdersRejected,
         m_testerOrdersSkippedByGate,
         GateFailureSummary(),
         m_lastGateFailure,
         eventName
      );
   }

   bool ProcessDecision(
      const SStrategyDecision &decision,
      const string symbol,
      const SUpcomersConfig &config,
      const bool isStrategyTesterRuntime,
      CMessageCounter &messageCounter,
      CStateManager &state,
      CUpcomersLogger &logger,
      const int spreadPoints,
      string &reason
   )
   {
      reason = "TESTER_EXECUTION_NO_ACTION";
      if(decision.Signal != SIGNAL_ENTER_LONG_INTENT &&
         decision.Signal != SIGNAL_ENTER_SHORT_INTENT)
      {
         reason = StringFormat(
            "TESTER_NO_ACTION_SIGNAL_NOT_EXECUTABLE signal=%s reason_code=%s waiting_for=ENTER_LONG_INTENT_OR_ENTER_SHORT_INTENT",
            SignalToString(decision.Signal),
            decision.ReasonCode
         );
         logger.Info("TesterExecution", reason);
         return false;
      }

      m_testerEntryIntentsReceived++;
      logger.Warn(
         "TesterExecution",
         StringFormat(
            "TESTER_ENTRY_INTENT_RECEIVED direction=%s sl=%.5f tp=%.5f spread=%d symbol=%s reason_code=%s",
            decision.Direction,
            decision.SuggestedStopLoss,
            decision.SuggestedTakeProfit,
            spreadPoints,
            symbol,
            decision.ReasonCode
         )
      );

      string configReason = "";
      if(!ValidateStrategyTesterExecutionConfig(config, isStrategyTesterRuntime, configReason))
      {
         LogGateFailure(
            logger,
            "ValidateStrategyTesterExecutionConfig",
            configReason,
            reason
         );
         return false;
      }

      if(!LogGate(logger, "MQL_TESTER", isStrategyTesterRuntime, BoolToText(isStrategyTesterRuntime), reason))
         return false;
      if(!LogGate(logger, "StrategyTesterExecutionMode", config.StrategyTesterExecutionMode, BoolToText(config.StrategyTesterExecutionMode), reason))
         return false;
      if(!LogGate(logger, "EnableTradingInputFalse", !config.EnableTrading, BoolToText(config.EnableTrading), reason))
         return false;
      if(!LogGate(logger, "EnableTrialExecutionFalse", !config.EnableTrialExecution, BoolToText(config.EnableTrialExecution), reason))
         return false;
      if(!LogGate(logger, "EnablePropChallengeModeFalse", !config.EnablePropChallengeMode, BoolToText(config.EnablePropChallengeMode), reason))
         return false;
      if(!LogGate(logger, "AccountProgramTrialRiskFree", config.AccountProgram == ACCOUNT_PROGRAM_TRIAL_RISK_FREE, AccountProgramToString(config.AccountProgram), reason))
         return false;
      if(!LogGate(logger, "AccountStageMonitorOnly", config.AccountStage == ACCOUNT_STAGE_MONITOR_ONLY, AccountStageToString(config.AccountStage), reason))
         return false;
      if(!LogGate(logger, "AllowedSymbols", IsStrategyTesterResearchSymbolAllowed(config.AllowedSymbols) && IsStrategyTesterResearchSymbolAllowed(symbol), "AllowedSymbols=" + config.AllowedSymbols + " symbol=" + symbol, reason))
         return false;
      if(!LogGate(logger, "StopLossRequired", config.StopLossRequired, BoolToText(config.StopLossRequired), reason))
         return false;
      if(!LogGate(logger, "MinHoldSeconds", config.MinHoldSeconds >= 180, IntegerToString(config.MinHoldSeconds), reason))
         return false;
      if(!LogGate(logger, "UseSpreadFilter", config.UseSpreadFilter, BoolToText(config.UseSpreadFilter), reason))
         return false;
      if(!LogGate(logger, "Spread", spreadPoints >= 0 && spreadPoints <= config.MaxSpreadPoints, StringFormat("spread=%d max=%d", spreadPoints, config.MaxSpreadPoints), reason))
         return false;
      if(!LogGate(logger, "PositionCapsTotal", PositionsTotal() < config.MaxOpenPositionsTotal, IntegerToString(PositionsTotal()), reason))
         return false;
      if(!LogGate(logger, "PositionCapsSymbol", CountOpenPositionsForSymbol(symbol) < config.MaxOpenPositionsPerSymbol, IntegerToString(CountOpenPositionsForSymbol(symbol)), reason))
         return false;
      if(!LogGate(logger, "TradeAttemptsToday", messageCounter.TradeIntentEvents() + 1 <= config.MaxTradesPerDay, IntegerToString(messageCounter.TradeIntentEvents()), reason))
         return false;
      if(!LogGate(logger, "ServerMessagesToday", messageCounter.ActualServerMessages() + 1 <= config.MaxServerMessagesPerDay, IntegerToString(messageCounter.ActualServerMessages()), reason))
         return false;

      string attemptKey = BuildAttemptKey(decision, symbol);
      if(!LogGate(logger, "OneAttemptPerSignal", !m_hasLastAttemptKey || m_lastAttemptKey != attemptKey, attemptKey, reason))
         return false;

      double ask = 0.0;
      double bid = 0.0;
      if(!SymbolInfoDouble(symbol, SYMBOL_ASK, ask) || ask <= 0.0 ||
         !SymbolInfoDouble(symbol, SYMBOL_BID, bid) || bid <= 0.0)
      {
         LogGateFailure(logger, "BidAsk", "unable to read bid/ask", reason);
         return false;
      }
      long digits = 0;
      double point = 0.0;
      string metadataReason = "";
      if(!ReadPositivePriceMetadata(symbol, digits, point, metadataReason))
      {
         LogGateFailure(logger, "SymbolMetadata", metadataReason, reason);
         return false;
      }
      double entryPriceRaw = (decision.Signal == SIGNAL_ENTER_LONG_INTENT ? ask : bid);
      double entryPrice = NormalizeDouble(entryPriceRaw, (int)digits);
      string slTpReason = "";
      if(!ValidateStopAndTakeProfit(symbol, decision, entryPrice, slTpReason))
      {
         LogGateFailure(logger, "SLTP", slTpReason, reason);
         return false;
      }
      logger.Info("TesterExecution", "TESTER_EXECUTION_GATE SLTP=true " + slTpReason);

      double volume = 0.0;
      string lotReason = "";
      if(!ResolveMinimumTesterLot(symbol, config, entryPrice, decision.SuggestedStopLoss, volume, lotReason))
      {
         LogGateFailure(logger, "LotSize", lotReason, reason);
         return false;
      }
      logger.Info("TesterExecution", "TESTER_EXECUTION_GATE LotSize=true " + lotReason);

      double normalizedStopLoss = NormalizeDouble(decision.SuggestedStopLoss, (int)digits);
      double normalizedTakeProfit = NormalizeDouble(decision.SuggestedTakeProfit, (int)digits);
      string normalizedGeometryReason = "";
      if(!ValidateRequestGeometry(
         symbol,
         decision.Signal,
         entryPrice,
         normalizedStopLoss,
         normalizedTakeProfit,
         normalizedGeometryReason
      ))
      {
         LogGateFailure(logger, "SLTP", normalizedGeometryReason, reason);
         return false;
      }
      logger.Info(
         "TesterExecution",
         StringFormat(
            "TESTER_ORDER_NORMALIZED price_raw=%.8f price=%.8f sl_raw=%.8f sl=%.8f tp_raw=%.8f tp=%.8f digits=%d point=%.10f %s",
            entryPriceRaw,
            entryPrice,
            decision.SuggestedStopLoss,
            normalizedStopLoss,
            decision.SuggestedTakeProfit,
            normalizedTakeProfit,
            (int)digits,
            point,
            normalizedGeometryReason
         )
      );

      long symbolFillingMode = -1;
      string fillingReason = "";
      ENUM_ORDER_TYPE_FILLING fillingMode = ResolveTesterFillingMode(
         symbol,
         symbolFillingMode,
         fillingReason
      );
      logger.Info("TesterExecution", "TESTER_FILLING_MODE " + fillingReason);

      ENUM_ORDER_TYPE orderType = (
         decision.Signal == SIGNAL_ENTER_LONG_INTENT ? ORDER_TYPE_BUY : ORDER_TYPE_SELL
      );
      MqlTradeRequest request;
      MqlTradeResult result;
      ZeroMemory(request);
      ZeroMemory(result);
      request.action = TRADE_ACTION_DEAL;
      request.symbol = symbol;
      request.volume = volume;
      request.type = orderType;
      request.price = entryPrice;
      request.sl = normalizedStopLoss;
      request.tp = normalizedTakeProfit;
      request.deviation = 10;
      request.type_filling = fillingMode;
      request.magic = (ulong)(config.TrialExecutionMagicNumber + 1);
      request.comment = "Strategy Tester simulated execution only";

      long diagnosticFillingMode = -1;
      long diagnosticTradeMode = -1;
      long diagnosticStopsLevel = -1;
      long diagnosticFreezeLevel = -1;
      double diagnosticVolumeMin = -1.0;
      double diagnosticVolumeStep = -1.0;
      double diagnosticBid = -1.0;
      double diagnosticAsk = -1.0;
      double diagnosticPoint = -1.0;
      long diagnosticDigits = -1;
      ReadOrderSymbolDiagnostics(
         symbol,
         diagnosticFillingMode,
         diagnosticTradeMode,
         diagnosticStopsLevel,
         diagnosticFreezeLevel,
         diagnosticVolumeMin,
         diagnosticVolumeStep,
         diagnosticBid,
         diagnosticAsk,
         diagnosticPoint,
         diagnosticDigits
      );
      string requestDiagnostics = TesterOrderRequestDiagnostics(
         request,
         diagnosticFillingMode,
         diagnosticTradeMode,
         diagnosticStopsLevel,
         diagnosticFreezeLevel,
         diagnosticVolumeMin,
         diagnosticVolumeStep,
         diagnosticBid,
         diagnosticAsk,
         diagnosticPoint,
         diagnosticDigits
      );

      logger.Warn(
         "TesterExecution",
         StringFormat(
            "TESTER_ORDER_REQUEST symbol=%s type=%s volume=%.8f price=%.8f sl=%.8f tp=%.8f type_filling=%s %s",
            symbol,
            EnumToString(orderType),
            volume,
            request.price,
            request.sl,
            request.tp,
            EnumToString(request.type_filling),
            requestDiagnostics
         )
      );

      logger.Warn(
         "TesterExecution",
         StringFormat(
            "TESTER_EXECUTION_APPROVED simulated tester order symbol=%s type=%s volume=%.4f price=%.5f sl=%.5f tp=%.5f spread=%d min_hold_seconds=%d no_retry=true",
            symbol,
            EnumToString(orderType),
            volume,
            request.price,
            request.sl,
            request.tp,
            spreadPoints,
            config.MinHoldSeconds
         )
      );

      m_lastAttemptKey = attemptKey;
      m_hasLastAttemptKey = true;
      messageCounter.RecordTradeIntentEvent();

      // TESTER_NO_RETRY_ORDER_SEND_ONCE: exactly one simulated request is sent for a validated tester signal.
      m_testerOrdersAttempted++;
      bool sent = OrderSend(request, result);
      messageCounter.RecordActualServerMessage();
      logger.Warn(
         "TesterExecution",
         StringFormat(
            "TESTER_EXECUTION_BROKER_RESPONSE simulated=true sent=%s retcode=%u order=%I64u deal=%I64u comment=%s no_retry=true %s",
            BoolToText(sent),
            result.retcode,
            result.order,
            result.deal,
            result.comment,
            requestDiagnostics
         )
      );

      if(!sent || (result.retcode != TRADE_RETCODE_DONE && result.retcode != TRADE_RETCODE_PLACED))
      {
         m_testerOrdersRejected++;
         reason = StringFormat(
            "TESTER_EXECUTION_ORDER_REJECTED retcode=%u comment=%s no retry for this signal %s",
            result.retcode,
            result.comment,
            requestDiagnostics
         );
         logger.Warn("TesterExecution", reason);
         return false;
      }

      m_testerOrdersSentSuccess++;
      state.SetFutureOpenTimeStub(TimeCurrent());
      reason = StringFormat(
         "TESTER_EXECUTION_ORDER_ACCEPTED simulated=true order=%I64u deal=%I64u min_hold_seconds=%d",
         result.order,
         result.deal,
         config.MinHoldSeconds
      );
      logger.Warn("TesterExecution", reason);
      return true;
   }
};

#endif

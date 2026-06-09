#ifndef UPCOMERS_NY_SESSION_PROP_BOT_TRIAL_EXECUTION_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_TRIAL_EXECUTION_MQH

#include "Config.mqh"
#include "Logger.mqh"
#include "MessageCounter.mqh"
#include "StateManager.mqh"
#include "StrategyBase.mqh"

class CTrialExecutionManager
{
private:
   string m_lastAttemptKey;
   bool m_hasLastAttemptKey;

   bool LogGate(
      CUpcomersLogger &logger,
      const string gateName,
      const bool passed,
      const string detail,
      string &reason
   )
   {
      string message = StringFormat("TRIAL_EXECUTION_GATE %s=%s %s", gateName, BoolToText(passed), detail);
      if(passed)
         logger.Info("TrialExecution", message);
      else
      {
         logger.Warn("TrialExecution", message);
         reason = "TRIAL_EXECUTION_DENIED gate=" + gateName + " detail=" + detail;
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

   bool ResolveMinimumSafeLot(
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
            "broker minimum lot %.4f exceeds conservative risk-based lot %.4f; no order sent",
            minVolume,
            riskBasedLot
         );
         return false;
      }

      volume = minVolume;
      if(volumeStep > 0.0)
         volume = MathFloor(volume / volumeStep) * volumeStep;
      if(volume < minVolume)
         volume = minVolume;
      reason = StringFormat(
         "fixed minimum lot selected volume=%.4f min=%.4f risk_based_lot=%.4f risk_pct=%.2f",
         volume,
         minVolume,
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
         reason = "SL/TP required: strategy intent must include both stop-loss and take-profit";
         return false;
      }
      if(decision.Signal == SIGNAL_ENTER_LONG_INTENT)
      {
         if(decision.SuggestedStopLoss >= entryPrice || decision.SuggestedTakeProfit <= entryPrice)
         {
            reason = "invalid LONG SL/TP geometry";
            return false;
         }
      }
      else if(decision.Signal == SIGNAL_ENTER_SHORT_INTENT)
      {
         if(decision.SuggestedStopLoss <= entryPrice || decision.SuggestedTakeProfit >= entryPrice)
         {
            reason = "invalid SHORT SL/TP geometry";
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
            "SL/TP geometry and STOP_LEVEL_CONSTRAINT validated stops_level_points=%d",
            (int)stopsLevelPoints
         );
         return true;
      }
      if(!hasStopsLevel)
      {
         reason = "SL/TP geometry validated; SYMBOL_TRADE_STOPS_LEVEL unavailable";
         return true;
      }
      reason = "SL/TP geometry validated";
      return true;
   }

public:
   void Reset()
   {
      m_lastAttemptKey = "";
      m_hasLastAttemptKey = false;
   }

   bool ProcessDecision(
      const SStrategyDecision &decision,
      const string symbol,
      const SUpcomersConfig &config,
      CMessageCounter &messageCounter,
      CStateManager &state,
      CUpcomersLogger &logger,
      const int spreadPoints,
      string &reason
   )
   {
      reason = "TRIAL_EXECUTION_NO_ACTION";
      if(decision.Signal != SIGNAL_ENTER_LONG_INTENT &&
         decision.Signal != SIGNAL_ENTER_SHORT_INTENT)
      {
         if(config.EnableTrading && config.EnableTrialExecution)
         {
            string readinessReason = "";
            if(!ValidateTrialExecutionConfig(config, readinessReason))
            {
               reason = "TRIAL_EXECUTION_DENIED gate=ValidateTrialExecutionConfig detail=" + readinessReason;
               logger.Warn("TrialExecution", reason);
               return false;
            }
            if(decision.Signal == SIGNAL_SETUP_FORMING)
            {
               reason = "NO_ACTION_SIGNAL_NOT_EXECUTABLE signal=SETUP_FORMING waiting_for=ENTER_LONG_INTENT_OR_ENTER_SHORT_INTENT";
               logger.Info("TrialExecution", reason);
               return false;
            }
            reason = StringFormat(
               "ARMED_TRIAL_EXECUTION_WAITING_FOR_VALID_SIGNAL signal=%s waiting_for=ENTER_LONG_INTENT_OR_ENTER_SHORT_INTENT",
               SignalToString(decision.Signal)
            );
            logger.Info("TrialExecution", reason);
         }
         return false;
      }

      string gateReason = "";
      bool configValid = ValidateTrialExecutionConfig(config, gateReason);
      if(!LogGate(logger, "ValidateTrialExecutionConfig", configValid, gateReason, reason))
         return false;
      if(!LogGate(logger, "AccountProgramTrialRiskFree", config.AccountProgram == ACCOUNT_PROGRAM_TRIAL_RISK_FREE, AccountProgramToString(config.AccountProgram), reason))
         return false;
      if(!LogGate(logger, "AccountStageTrial", config.AccountStage == ACCOUNT_STAGE_TRIAL, AccountStageToString(config.AccountStage), reason))
         return false;
      if(!LogGate(logger, "EnableTrading", config.EnableTrading, BoolToText(config.EnableTrading), reason))
         return false;
      if(!LogGate(logger, "EnableTrialExecution", config.EnableTrialExecution, BoolToText(config.EnableTrialExecution), reason))
         return false;
      if(!LogGate(logger, "EnablePropChallengeModeFalse", !config.EnablePropChallengeMode, BoolToText(config.EnablePropChallengeMode), reason))
         return false;
      if(!LogGate(logger, "ManualConfirmationText", HasTrialExecutionConfirmation(config), "exact Trial Risk-Free phrase required", reason))
         return false;
      if(!LogGate(logger, "SourceScanPassId", HasText(config.SourceScanPassId), config.SourceScanPassId, reason))
         return false;
      if(!LogGate(logger, "StopLossRequired", config.StopLossRequired, BoolToText(config.StopLossRequired), reason))
         return false;
      if(!LogGate(logger, "MinHoldSeconds", config.MinHoldSeconds >= 180, IntegerToString(config.MinHoldSeconds), reason))
         return false;
      if(!LogGate(logger, "MaxRiskPerTradePct", config.MaxRiskPerTradePct <= 0.50, DoubleToString(config.MaxRiskPerTradePct, 2), reason))
         return false;
      if(!LogGate(logger, "RiskPerTradePct", config.RiskPerTradePct <= 0.25, DoubleToString(config.RiskPerTradePct, 2), reason))
         return false;
      if(!LogGate(logger, "MaxOpenPositionsTotal", config.MaxOpenPositionsTotal == 1, IntegerToString(config.MaxOpenPositionsTotal), reason))
         return false;
      if(!LogGate(logger, "MaxOpenPositionsPerSymbol", config.MaxOpenPositionsPerSymbol == 1, IntegerToString(config.MaxOpenPositionsPerSymbol), reason))
         return false;
      if(!LogGate(logger, "MaxTradesPerDay", config.MaxTradesPerDay == 1, IntegerToString(config.MaxTradesPerDay), reason))
         return false;
      if(!LogGate(logger, "MaxServerMessagesPerDay", config.MaxServerMessagesPerDay <= 500, IntegerToString(config.MaxServerMessagesPerDay), reason))
         return false;
      if(!LogGate(logger, "AllowedSymbols", config.AllowedSymbols == "EURUSD" && symbol == "EURUSD", "AllowedSymbols=" + config.AllowedSymbols + " symbol=" + symbol, reason))
         return false;
      if(!LogGate(logger, "UseSpreadFilter", config.UseSpreadFilter, BoolToText(config.UseSpreadFilter), reason))
         return false;
      if(!LogGate(logger, "RequireBrokerTimeValidation", config.RequireBrokerTimeValidation, BoolToText(config.RequireBrokerTimeValidation), reason))
         return false;
      if(!LogGate(logger, "BrokerTimeValidationNote", HasText(config.BrokerTimeValidationNote), config.BrokerTimeValidationNote, reason))
         return false;
      if(!LogGate(logger, "Spread", spreadPoints >= 0 && spreadPoints <= config.MaxSpreadPoints, StringFormat("spread=%d max=%d", spreadPoints, config.MaxSpreadPoints), reason))
         return false;

      int totalPositions = PositionsTotal();
      int symbolPositions = CountOpenPositionsForSymbol(symbol);
      if(!LogGate(logger, "PositionCapsTotal", totalPositions < config.MaxOpenPositionsTotal, IntegerToString(totalPositions), reason))
         return false;
      if(!LogGate(logger, "PositionCapsSymbol", symbolPositions < config.MaxOpenPositionsPerSymbol, IntegerToString(symbolPositions), reason))
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
         reason = "TRIAL_EXECUTION_DENIED unable to read bid/ask";
         logger.Warn("TrialExecution", reason);
         return false;
      }
      double entryPrice = (decision.Signal == SIGNAL_ENTER_LONG_INTENT ? ask : bid);
      string slTpReason = "";
      if(!ValidateStopAndTakeProfit(symbol, decision, entryPrice, slTpReason))
      {
         reason = "TRIAL_EXECUTION_DENIED " + slTpReason;
         logger.Warn("TrialExecution", reason);
         return false;
      }
      logger.Info("TrialExecution", "TRIAL_EXECUTION_GATE SLTP=true " + slTpReason);

      double volume = 0.0;
      string lotReason = "";
      if(!ResolveMinimumSafeLot(symbol, config, entryPrice, decision.SuggestedStopLoss, volume, lotReason))
      {
         reason = "TRIAL_EXECUTION_DENIED " + lotReason;
         logger.Warn("TrialExecution", reason);
         return false;
      }
      logger.Info("TrialExecution", "TRIAL_EXECUTION_GATE LotSize=true " + lotReason);

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
      request.sl = decision.SuggestedStopLoss;
      request.tp = decision.SuggestedTakeProfit;
      request.deviation = 10;
      request.magic = (ulong)config.TrialExecutionMagicNumber;
      request.comment = "TrialRiskFree micro execution only";

      logger.Warn(
         "TrialExecution",
         StringFormat(
            "TRIAL_EXECUTION_APPROVED TrialRiskFree-only order request symbol=%s type=%s volume=%.4f price=%.5f sl=%.5f tp=%.5f spread=%d magic=%d no_retry=true",
            symbol,
            EnumToString(orderType),
            volume,
            request.price,
            request.sl,
            request.tp,
            spreadPoints,
            config.TrialExecutionMagicNumber
         )
      );

      m_lastAttemptKey = attemptKey;
      m_hasLastAttemptKey = true;
      messageCounter.RecordTradeIntentEvent();

      // NO_RETRY_ORDER_SEND_ONCE: exactly one market request is sent for a validated Trial signal.
      bool sent = OrderSend(request, result);
      messageCounter.RecordActualServerMessage();
      logger.Warn(
         "TrialExecution",
         StringFormat(
            "TRIAL_EXECUTION_BROKER_RESPONSE sent=%s retcode=%u order=%I64u deal=%I64u comment=%s no_retry=true",
            BoolToText(sent),
            result.retcode,
            result.order,
            result.deal,
            result.comment
         )
      );

      if(!sent || (result.retcode != TRADE_RETCODE_DONE && result.retcode != TRADE_RETCODE_PLACED))
      {
         reason = StringFormat(
            "TRIAL_EXECUTION_ORDER_REJECTED retcode=%u no retry for this signal",
            result.retcode
         );
         logger.Warn("TrialExecution", reason);
         return false;
      }

      state.SetFutureOpenTimeStub(TimeCurrent());
      reason = StringFormat(
         "TRIAL_EXECUTION_ORDER_ACCEPTED TrialRiskFree-only order=%I64u deal=%I64u min_hold_seconds=%d",
         result.order,
         result.deal,
         config.MinHoldSeconds
      );
      logger.Warn("TrialExecution", reason);
      return true;
   }
};

#endif

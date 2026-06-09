#ifndef UPCOMERS_NY_SESSION_PROP_BOT_RISK_MANAGER_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_RISK_MANAGER_MQH

#include "Config.mqh"

struct SHypotheticalTradeIntent
{
   string SymbolName;
   bool HasStopLoss;
   double EstimatedRiskPct;
   int CurrentOpenPositionsTotal;
   int CurrentOpenPositionsForSymbol;
   double EstimatedSpreadPoints;
};

class CRiskManager
{
public:
   void BuildMonitorOnlyIntent(
      const string symbol,
      const SUpcomersConfig &config,
      SHypotheticalTradeIntent &intent
   )
   {
      intent.SymbolName = symbol;
      intent.HasStopLoss = config.StopLossRequired;
      intent.EstimatedRiskPct = config.RiskPerTradePct;
      intent.CurrentOpenPositionsTotal = 0;
      intent.CurrentOpenPositionsForSymbol = 0;
      intent.EstimatedSpreadPoints = 0.0;
   }

   bool CheckRisk(const SUpcomersConfig &config, string &reason)
   {
      if(config.RiskPerTradePct > config.MaxRiskPerTradePct)
      {
         reason = "RiskPerTradePct exceeds MaxRiskPerTradePct";
         return false;
      }
      if(config.MaxRiskPerTradePct > 0.50)
      {
         reason = "MaxRiskPerTradePct exceeds absolute Phase 5 cap";
         return false;
      }
      if(config.MaxDailyLossHardPct >= 4.0 || config.MaxOverallLossHardPct >= 7.0)
      {
         reason = "loss guards must remain stricter than prop-firm caps";
         return false;
      }
      if(config.MinHoldSeconds < 180)
      {
         reason = "MinHoldSeconds guard failed";
         return false;
      }
      if(!config.StopLossRequired)
      {
         reason = "StopLossRequired guard failed";
         return false;
      }
      if(config.MaxOpenPositionsTotal < 1 || config.MaxOpenPositionsPerSymbol < 1)
      {
         reason = "position cap guard failed";
         return false;
      }
      reason = "risk checks are monitor-only stubs in Phase 5";
      return true;
   }

   bool CheckHypotheticalTradeIntent(
      const SUpcomersConfig &config,
      const SHypotheticalTradeIntent &intent,
      string &reason
   )
   {
      if(StringLen(intent.SymbolName) == 0)
      {
         reason = "hypothetical intent rejected: missing symbol";
         return false;
      }
      if(config.StopLossRequired && !intent.HasStopLoss)
      {
         reason = "hypothetical intent rejected: StopLossRequired guard";
         return false;
      }
      if(intent.EstimatedRiskPct > config.MaxRiskPerTradePct || intent.EstimatedRiskPct > 0.50)
      {
         reason = "hypothetical intent rejected: estimated risk exceeds cap";
         return false;
      }
      if(intent.CurrentOpenPositionsTotal >= config.MaxOpenPositionsTotal)
      {
         reason = "hypothetical intent rejected: total position cap";
         return false;
      }
      if(intent.CurrentOpenPositionsForSymbol >= config.MaxOpenPositionsPerSymbol)
      {
         reason = "hypothetical intent rejected: symbol position cap";
         return false;
      }
      reason = "hypothetical intent risk guard passed for non-execution estimate only";
      return true;
   }
};

#endif

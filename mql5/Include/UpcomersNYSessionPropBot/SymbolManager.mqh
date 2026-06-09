#ifndef UPCOMERS_NY_SESSION_PROP_BOT_SYMBOL_MANAGER_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_SYMBOL_MANAGER_MQH

#include "Config.mqh"

class CSymbolManager
{
public:
   bool CheckSymbol(const string symbol, string &reason)
   {
      if(StringLen(symbol) == 0)
      {
         reason = "symbol is empty";
         return false;
      }
      reason = StringFormat("symbol checks are monitor-only stubs for %s", symbol);
      return true;
   }

   bool TryReadSpreadPoints(const string symbol, int &spreadPoints, string &reason)
   {
      spreadPoints = -1;
      long integerSpread = 0;
      if(SymbolInfoInteger(symbol, SYMBOL_SPREAD, integerSpread) && integerSpread >= 0)
      {
         spreadPoints = (int)integerSpread;
         reason = StringFormat("spread read from SYMBOL_SPREAD: %d points", spreadPoints);
         return true;
      }

      double ask = 0.0;
      double bid = 0.0;
      double point = 0.0;
      bool hasAsk = SymbolInfoDouble(symbol, SYMBOL_ASK, ask);
      bool hasBid = SymbolInfoDouble(symbol, SYMBOL_BID, bid);
      bool hasPoint = SymbolInfoDouble(symbol, SYMBOL_POINT, point);
      if(hasAsk && hasBid && hasPoint && point > 0.0 && ask >= bid)
      {
         spreadPoints = (int)MathRound((ask - bid) / point);
         reason = StringFormat("spread computed from ask/bid: %d points", spreadPoints);
         return true;
      }

      reason = "SPREAD_UNKNOWN: unable to read SYMBOL_SPREAD or ask/bid metadata";
      return false;
   }

   bool CheckSpread(
      const string symbol,
      const SUpcomersConfig &config,
      int &spreadPoints,
      string &reason
   )
   {
      if(!config.UseSpreadFilter)
      {
         spreadPoints = 0;
         reason = "SPREAD_FILTER_DISABLED: spread filter is disabled";
         return true;
      }

      string spreadReason = "";
      if(!TryReadSpreadPoints(symbol, spreadPoints, spreadReason))
      {
         reason = spreadReason;
         if(config.SpreadUnknownBlocksTrading)
            reason = reason + "; SpreadUnknownBlocksTrading=true so monitor signal is SKIP_SPREAD";
         return !config.SpreadUnknownBlocksTrading;
      }

      if(spreadPoints > config.MaxSpreadPoints)
      {
         reason = StringFormat(
            "SPREAD_BLOCK: observed=%d threshold=%d points for %s",
            spreadPoints,
            config.MaxSpreadPoints,
            symbol
         );
         return false;
      }
      reason = StringFormat(
         "SPREAD_OK: observed=%d threshold=%d points for %s (%s)",
         spreadPoints,
         config.MaxSpreadPoints,
         symbol,
         spreadReason
      );
      return true;
   }
};

#endif

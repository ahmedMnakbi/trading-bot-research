#ifndef UPCOMERS_NY_SESSION_PROP_BOT_SESSION_MANAGER_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_SESSION_MANAGER_MQH

#include "Config.mqh"

#define UPCOMERS_NY_INDEX_CASH_START_MINUTE 570
#define UPCOMERS_NY_INDEX_CASH_END_MINUTE 960
#define UPCOMERS_NY_MULTI_ASSET_START_MINUTE 480
#define UPCOMERS_NY_MULTI_ASSET_END_MINUTE 1020
#define UPCOMERS_NY_OVERLAP_REFERENCE_START_MINUTE 420
#define UPCOMERS_NY_OVERLAP_REFERENCE_END_MINUTE 480
#define UPCOMERS_NY_OVERLAP_START_MINUTE 480
#define UPCOMERS_NY_OVERLAP_END_MINUTE 720
#define UPCOMERS_NY_OVERLAP_LAST_SIGNAL_MINUTE 715

class CSessionManager
{
private:
   ENUM_UPCOMERS_BROKER_TIME_MODE m_brokerTimeMode;
   int m_brokerServerUtcOffsetMinutes;
   bool m_requireBrokerTimeValidation;
   string m_brokerTimeValidationNote;

   bool MinuteInRange(const int minuteOfDay, const int startMinute, const int endMinute)
   {
      if(startMinute <= endMinute)
         return minuteOfDay >= startMinute && minuteOfDay < endMinute;
      return minuteOfDay >= startMinute || minuteOfDay < endMinute;
   }

   datetime UtcDateTime(
      const int year,
      const int month,
      const int day,
      const int hour,
      const int minute
   )
   {
      MqlDateTime parts;
      parts.year = year;
      parts.mon = month;
      parts.day = day;
      parts.hour = hour;
      parts.min = minute;
      parts.sec = 0;
      parts.day_of_week = 0;
      parts.day_of_year = 0;
      return StructToTime(parts);
   }

   int DayOfWeekUtc(const int year, const int month, const int day)
   {
      MqlDateTime parts;
      TimeToStruct(UtcDateTime(year, month, day, 0, 0), parts);
      return parts.day_of_week;
   }

   int NthSundayOfMonth(const int year, const int month, const int nth)
   {
      int firstSunday = 1;
      for(int day = 1; day <= 7; day++)
      {
         if(DayOfWeekUtc(year, month, day) == 0)
         {
            firstSunday = day;
            break;
         }
      }
      return firstSunday + ((nth - 1) * 7);
   }

   int MinuteOfDay(const MqlDateTime &parts)
   {
      return parts.hour * 60 + parts.min;
   }

   bool IsWeekday(const MqlDateTime &parts)
   {
      return parts.day_of_week != 0 && parts.day_of_week != 6;
   }

   int SessionDateKeyFromNewYork(const datetime newYorkTime)
   {
      MqlDateTime parts;
      TimeToStruct(newYorkTime, parts);
      return parts.year * 10000 + parts.mon * 100 + parts.day;
   }

public:
   CSessionManager()
   {
      m_brokerTimeMode = BROKER_TIME_MANUAL_UTC_OFFSET;
      m_brokerServerUtcOffsetMinutes = 0;
      m_requireBrokerTimeValidation = true;
      m_brokerTimeValidationNote = "";
   }

   void ConfigureBrokerTime(const SUpcomersConfig &config)
   {
      m_brokerTimeMode = config.BrokerTimeMode;
      m_brokerServerUtcOffsetMinutes = config.BrokerServerUtcOffsetMinutes;
      m_requireBrokerTimeValidation = config.RequireBrokerTimeValidation;
      m_brokerTimeValidationNote = config.BrokerTimeValidationNote;
   }

   bool CheckSession(const datetime serverTime, string &reason)
   {
      datetime utcTime = 0;
      datetime newYorkTime = 0;
      string timeReason = "";
      if(!ConvertBrokerServerToUtc(serverTime, utcTime, timeReason))
      {
         reason = timeReason;
         return false;
      }
      if(!ConvertUtcToNewYork(utcTime, newYorkTime, timeReason))
      {
         reason = timeReason;
         return false;
      }
      reason = StringFormat(
         "Phase 9 session clock ok server=%s utc=%s new_york=%s mode=%s offset_minutes=%d",
         TimeToString(serverTime, TIME_DATE | TIME_SECONDS),
         TimeToString(utcTime, TIME_DATE | TIME_SECONDS),
         TimeToString(newYorkTime, TIME_DATE | TIME_SECONDS),
         BrokerTimeModeToString(m_brokerTimeMode),
         m_brokerServerUtcOffsetMinutes
      );
      if(m_requireBrokerTimeValidation && StringLen(m_brokerTimeValidationNote) == 0)
         reason = reason + " validation_note_missing_before_trial_observation";
      return true;
   }

   bool ConvertBrokerServerToUtc(
      const datetime serverTime,
      datetime &utcTime,
      string &reason
   )
   {
      utcTime = 0;
      if(serverTime <= 0)
      {
         reason = "NY_TIME_UNAVAILABLE: broker server timestamp missing";
         return false;
      }
      if(m_brokerTimeMode != BROKER_TIME_MANUAL_UTC_OFFSET)
      {
         reason = "NY_TIME_UNAVAILABLE: unsupported BrokerTimeMode";
         return false;
      }
      utcTime = serverTime - (m_brokerServerUtcOffsetMinutes * 60);
      reason = StringFormat(
         "server timestamp converted to UTC using explicit broker offset %d minutes",
         m_brokerServerUtcOffsetMinutes
      );
      return true;
   }

   bool IsNewYorkDaylightSavingUtc(const datetime utcTime)
   {
      if(utcTime <= 0)
         return false;
      MqlDateTime parts;
      TimeToStruct(utcTime, parts);
      int year = parts.year;
      int marchSecondSunday = NthSundayOfMonth(year, 3, 2);
      int novemberFirstSunday = NthSundayOfMonth(year, 11, 1);
      datetime dstStartUtc = UtcDateTime(year, 3, marchSecondSunday, 7, 0);
      datetime dstEndUtc = UtcDateTime(year, 11, novemberFirstSunday, 6, 0);
      return utcTime >= dstStartUtc && utcTime < dstEndUtc;
   }

   int NewYorkUtcOffsetMinutesForUtc(const datetime utcTime)
   {
      return IsNewYorkDaylightSavingUtc(utcTime) ? -240 : -300;
   }

   bool ConvertUtcToNewYork(
      const datetime utcTime,
      datetime &newYorkTime,
      string &reason
   )
   {
      newYorkTime = 0;
      if(utcTime <= 0)
      {
         reason = "NY_TIME_UNAVAILABLE: UTC timestamp missing";
         return false;
      }
      int offsetMinutes = NewYorkUtcOffsetMinutesForUtc(utcTime);
      newYorkTime = utcTime + (offsetMinutes * 60);
      reason = StringFormat(
         "UTC converted to America/New_York with DST-aware offset %d minutes",
         offsetMinutes
      );
      return true;
   }

   bool TryConvertBrokerServerToNewYork(
      const datetime serverTime,
      datetime &newYorkTime,
      string &reason
   )
   {
      datetime utcTime = 0;
      if(!ConvertBrokerServerToUtc(serverTime, utcTime, reason))
         return false;
      if(!ConvertUtcToNewYork(utcTime, newYorkTime, reason))
         return false;
      reason = StringFormat(
         "server=%s utc=%s america_new_york=%s broker_offset_minutes=%d",
         TimeToString(serverTime, TIME_DATE | TIME_SECONDS),
         TimeToString(utcTime, TIME_DATE | TIME_SECONDS),
         TimeToString(newYorkTime, TIME_DATE | TIME_SECONDS),
         m_brokerServerUtcOffsetMinutes
      );
      return true;
   }

   bool IsIndexSymbol(const string symbol)
   {
      string upper = symbol;
      StringToUpper(upper);
      return StringFind(upper, "US30") >= 0 ||
             StringFind(upper, "DJ") >= 0 ||
             StringFind(upper, "NAS") >= 0 ||
             StringFind(upper, "USTEC") >= 0 ||
             StringFind(upper, "US100") >= 0 ||
             StringFind(upper, "SPX") >= 0 ||
             StringFind(upper, "US500") >= 0;
   }

   bool IsFxGoldCryptoSymbol(const string symbol)
   {
      string upper = symbol;
      StringToUpper(upper);
      return StringFind(upper, "XAU") >= 0 ||
             StringFind(upper, "GOLD") >= 0 ||
             StringFind(upper, "EUR") >= 0 ||
             StringFind(upper, "GBP") >= 0 ||
             StringFind(upper, "USD") >= 0 ||
             StringFind(upper, "JPY") >= 0 ||
             StringFind(upper, "CHF") >= 0 ||
             StringFind(upper, "CAD") >= 0 ||
             StringFind(upper, "AUD") >= 0 ||
             StringFind(upper, "NZD") >= 0 ||
             StringFind(upper, "BTC") >= 0 ||
             StringFind(upper, "ETH") >= 0;
   }

   string StringToUpperCopy(const string value)
   {
      string copy = value;
      StringToUpper(copy);
      return copy;
   }

   string SymbolClassFor(const string symbol)
   {
      string upper = StringToUpperCopy(symbol);
      if(IsIndexSymbol(symbol))
         return "US_INDEX_CFD";
      if(StringFind(upper, "XAU") >= 0 || StringFind(upper, "GOLD") >= 0)
         return "GOLD";
      if(StringFind(upper, "BTC") >= 0 || StringFind(upper, "ETH") >= 0)
         return "CRYPTO";
      return "FX_OR_OTHER";
   }

   string SessionTag(const string symbol)
   {
      if(IsIndexSymbol(symbol))
         return "US_INDEX_CASH_0930_1600_AMERICA_NEW_YORK";
      return "FX_GOLD_CRYPTO_NY_0800_1700_AMERICA_NEW_YORK";
   }

   string SessionTagForSymbol(const string symbol)
   {
      return SessionTag(symbol);
   }

   bool IsIndexCashSession(const datetime serverTime, const string symbol, string &reason)
   {
      if(serverTime <= 0 || StringLen(symbol) == 0)
      {
         reason = "SKIP_SESSION: index cash session cannot be determined";
         return false;
      }
      datetime newYorkTime = 0;
      if(!TryConvertBrokerServerToNewYork(serverTime, newYorkTime, reason))
         return false;
      MqlDateTime parts;
      TimeToStruct(newYorkTime, parts);
      if(!IsWeekday(parts))
      {
         reason = "SKIP_SESSION: outside weekday index cash session";
         return false;
      }
      if(!MinuteInRange(
         MinuteOfDay(parts),
         UPCOMERS_NY_INDEX_CASH_START_MINUTE,
         UPCOMERS_NY_INDEX_CASH_END_MINUTE
      ))
      {
         reason = "SKIP_SESSION: outside 09:30-16:00 America/New_York index cash session";
         return false;
      }
      reason = "US_INDEX_CASH_0930_1600_AMERICA_NEW_YORK gate passed";
      return true;
   }

   bool IsFxGoldCryptoNYSession(const datetime serverTime, const string symbol, string &reason)
   {
      if(serverTime <= 0 || StringLen(symbol) == 0)
      {
         reason = "SKIP_SESSION: FX/gold/crypto New York session cannot be determined";
         return false;
      }
      datetime newYorkTime = 0;
      if(!TryConvertBrokerServerToNewYork(serverTime, newYorkTime, reason))
         return false;
      MqlDateTime parts;
      TimeToStruct(newYorkTime, parts);
      if(!IsWeekday(parts))
      {
         reason = "SKIP_SESSION: outside weekday New York session";
         return false;
      }
      if(!MinuteInRange(
         MinuteOfDay(parts),
         UPCOMERS_NY_MULTI_ASSET_START_MINUTE,
         UPCOMERS_NY_MULTI_ASSET_END_MINUTE
      ))
      {
         reason = "SKIP_SESSION: outside 08:00-17:00 America/New_York FX/gold/crypto session";
         return false;
      }
      reason = "FX_GOLD_CRYPTO_NY_0800_1700_AMERICA_NEW_YORK gate passed";
      return true;
   }

   bool IsNewYorkSession(const datetime serverTime, const string symbol, string &reason)
   {
      return IsFxGoldCryptoNYSession(serverTime, symbol, reason);
   }

   bool IsLondonNewYorkOverlap(const datetime serverTime, const string symbol, string &reason)
   {
      if(serverTime <= 0 || StringLen(symbol) == 0)
      {
         reason = "SKIP_SESSION: London/New York overlap cannot be determined";
         return false;
      }
      datetime newYorkTime = 0;
      if(!TryConvertBrokerServerToNewYork(serverTime, newYorkTime, reason))
         return false;
      MqlDateTime parts;
      TimeToStruct(newYorkTime, parts);
      if(!IsWeekday(parts))
      {
         reason = "SKIP_SESSION: outside weekday London/New York overlap";
         return false;
      }
      int minute = MinuteOfDay(parts);
      if(IsNearSessionEnd(newYorkTime, 5))
      {
         reason = "LATE_OVERLAP_BLOCK: stop signaling near 11:55 America/New_York";
         return false;
      }
      if(!MinuteInRange(minute, UPCOMERS_NY_OVERLAP_START_MINUTE, UPCOMERS_NY_OVERLAP_END_MINUTE))
      {
         reason = "SKIP_SESSION: outside 08:00-12:00 America/New_York overlap";
         return false;
      }
      reason = "LONDON_NY_OVERLAP_0800_1200_AMERICA_NEW_YORK gate passed";
      return true;
   }

   bool IsNearSessionEnd(const datetime newYorkTime, const int bufferMinutes)
   {
      if(newYorkTime <= 0)
         return true;
      MqlDateTime parts;
      TimeToStruct(newYorkTime, parts);
      int minute = MinuteOfDay(parts);
      return minute >= (UPCOMERS_NY_OVERLAP_END_MINUTE - bufferMinutes);
   }

   bool IsEntrySessionForSymbol(const datetime serverTime, const string symbol, string &reason)
   {
      if(IsIndexSymbol(symbol))
         return IsIndexCashSession(serverTime, symbol, reason);
      return IsFxGoldCryptoNYSession(serverTime, symbol, reason);
   }

   int StrategySessionKey(const datetime serverTime)
   {
      if(serverTime <= 0)
         return 0;
      datetime newYorkTime = 0;
      string reason = "";
      if(!TryConvertBrokerServerToNewYork(serverTime, newYorkTime, reason))
         return 0;
      return SessionDateKeyFromNewYork(newYorkTime);
   }
};

#endif

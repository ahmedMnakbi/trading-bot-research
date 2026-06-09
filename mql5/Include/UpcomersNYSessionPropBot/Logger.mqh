#ifndef UPCOMERS_NY_SESSION_PROP_BOT_LOGGER_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_LOGGER_MQH

class CUpcomersLogger
{
public:
   void Info(const string component, const string message)
   {
      Print(StringFormat("[UpcomersNYSessionPropBot][%s][INFO] %s", component, message));
   }

   void Warn(const string component, const string message)
   {
      Print(StringFormat("[UpcomersNYSessionPropBot][%s][WARN] %s", component, message));
   }

   void Error(const string component, const string message)
   {
      Print(StringFormat("[UpcomersNYSessionPropBot][%s][ERROR] %s", component, message));
   }
};

#endif

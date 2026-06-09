#ifndef UPCOMERS_NY_SESSION_PROP_BOT_NEWS_FILTER_PLACEHOLDER_MQH
#define UPCOMERS_NY_SESSION_PROP_BOT_NEWS_FILTER_PLACEHOLDER_MQH

class CNewsFilterPlaceholder
{
public:
   bool IsNewsBlocked(string &reason)
   {
      reason = "HIGH_RISK_NEWS_NOT_APPROVED: placeholder has no automated news calendar; avoid high-risk news manually";
      return false;
   }
};

#endif

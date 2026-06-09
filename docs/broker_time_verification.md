# Broker Time Verification

Broker time verification is required before trusting session filters during Trial monitor-only observation. The EA does not assume broker server time equals New York time.

## Checklist

1. Open MT5 manually on the Trial Risk-Free account.
2. Observe Market Watch or platform server time.
3. Compare MT5 Market Watch/server time to UTC.
4. Calculate `BrokerServerUtcOffsetMinutes`.
5. Compare UTC against America/New_York time.
6. Update the EA input `BrokerServerUtcOffsetMinutes`.
7. Record the evidence manually as a note and screenshot.
8. Confirm the EA log prints server, UTC, and America/New_York timestamps.

## DST Risk

The EA applies U.S. New York DST rules after converting broker server time to UTC. Broker server offsets can change seasonally or vary by broker. Recheck the offset around DST transitions and whenever the broker changes server time.

Do not rely on session filters for Trial monitor-only observation until the broker offset and New York conversion are verified. This process does not require or request passwords.

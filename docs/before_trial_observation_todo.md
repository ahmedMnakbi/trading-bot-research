# Before Trial Observation TODO

The Phase 9 EA remains monitor-only and is not approved for Trial Risk-Free trading, Surge 2 Step, Vanguard, Challenge, Verification, Funded, or live use. Complete these items before any Trial monitor-only observation phase is considered:

- Verify `BrokerServerUtcOffsetMinutes` against the current MT5 server clock, UTC, and America/New_York time.
- Confirm DST-aware broker server time to New York conversion with current broker timestamps.
- Validate the DST-aware New York conversion around current session boundaries and daylight-saving transitions.
- Verify broker symbol sessions against New York windows: U.S. index cash 09:30-16:00, FX/gold/crypto 08:00-17:00, London/New York overlap 08:00-12:00.
- Confirm closed-bar-only strategy evaluation in real monitor logs.
- Verify opening range breakout minutes-to-bars handling on M1 range construction.
- Validate OnTick/OnTimer throttling with `EvaluationMode=OnNewClosedBar` and `MinEvaluationSeconds`.
- Verify the real spread gate against broker symbol metadata, including unknown-spread blocking.
- Validate trade/message counter semantics: monitor evaluations, trade intents, refused trade actions, and actual server/order messages remain separate.
- Confirm no actual server/order messages are counted in monitor-only mode because no orders are sent.
- Review and encode exact Surge 2 Step rules; keep `Surge2Step` rule-unverified until complete.
- Review exact Vanguard rules; keep Vanguard blocked until exact rules, Trial evidence, audit package, and human approval exist.
- Keep Python MT5 execution quarantined and support-only.
- Keep `AccountProgram` support limited to `TrialRiskFree`, `Vanguard`, `Surge2Step`, and `Custom`.

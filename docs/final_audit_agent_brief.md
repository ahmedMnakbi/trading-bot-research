# Final Audit Agent Brief

The native MQL5 EA audit package is a review artifact, not a deployment approval.

The Final Audit Agent should verify:

- Native MQL5 EA remains the only prop execution path.
- Python remains support-only and cannot control prop orders.
- Trading is disabled by default.
- Source scan PASS and compile PASS artifacts are present.
- Trial monitor-only EA logs are real and not simulated before any Trial observation claim.
- Trial observation evidence is present before any protected-stage discussion.
- Strategy Tester evidence is present before any tester-based claim.
- Surge 2 Step exact rules are reviewed and encoded before Surge use.
- Vanguard exact rules are reviewed before Vanguard use.
- Daily reset timezone and Dynamic Risk Shield calculations are confirmed from current Upcomers rules.
- Human approval metadata and audit package IDs exist before Challenge, Verification, Funded, or live-money use.

Trial, Surge 2 Step, Vanguard, Challenge, Verification, Funded, and live trading remain blocked until all required evidence and approvals exist.

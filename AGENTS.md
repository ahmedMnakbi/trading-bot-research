# Agent Instructions

- Native MQL5 Expert Advisor code is the only prop-firm execution path.
- Python is research, validation, reporting, scanning, settings generation, log parsing, and audit support only.
- Python-controlled MT5 execution is not allowed for Challenge, Verification, Funded, Surge 2 Step, Vanguard, or other prop deployment.
- Trading must stay disabled by default; monitor-only or Trial testing comes before any higher account stage.
- Do not add grid, martingale, averaging down, HFT, arbitrage, copy trading, one-shot challenge passing, or sub-2-minute scalping behavior.
- Do not copy community EA code into production without license review, simplification, and audit.
- Preserve tests, safety audits, source scans, documentation, and review artifacts in every phase.
- Report uncertainty before coding when account rules, broker behavior, or safety gates are unclear.
- Source scanning and audit artifacts are required before human review.

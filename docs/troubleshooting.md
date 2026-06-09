# Troubleshooting

## MT5 init code 32767 incorrect parameters

MT5 reports `initializing ... failed with code 32767 (incorrect parameters)` when the EA returns `INIT_PARAMETERS_INCORRECT` from `OnInit`. For this project, read the Experts log lines immediately before the failure.

Phase 13.3 adds explicit startup gate diagnostics:

- `INIT_PARAMETERS_INCORRECT: <reason>` gives the first validation reason.
- `GATE_FAIL_<NAME>` gives each failed gate.
- Each gate line includes `input_value`, `expected_value`, and `applies_to`.

Common Trial Risk-Free micro-execution gate failures:

- `GATE_FAIL_BROKER_TIME_VALIDATION_NOTE`: `BrokerTimeValidationNote` is blank. Verify the broker server UTC offset manually, regenerate the `.set` with `--broker-time-validation-note`, and retry only on Trial Risk-Free.
- `GATE_FAIL_SOURCE_SCAN_PASS_ID`: `SourceScanPassId` is blank. Run the MQL5 source scan and paste the saved PASS ID or artifact ID into the generator.
- `GATE_FAIL_TRIAL_ACCOUNT_STAGE`: `AccountStage` is not `Trial`.
- `GATE_FAIL_TRIAL_ACCOUNT_PROGRAM`: `AccountProgram` is not `TrialRiskFree`.
- `GATE_FAIL_TRIAL_MANUAL_CONFIRMATION_TEXT`: the exact Trial confirmation phrase is missing.
- `GATE_FAIL_TRIAL_ALLOWED_SYMBOLS`: `AllowedSymbols` is not exactly `EURUSD`.
- `GATE_FAIL_TRIAL_USE_SPREAD_FILTER`: the spread filter is disabled.

For Trial Risk-Free micro-execution, the EA does not require `HumanApprovalId`, `FinalAuditPackageId`, `TrialEvidenceId`, `AccountProgramRulesReviewId`, or `DynamicRiskShieldConfirmationId`. Those remain protected-stage metadata gates for Surge 2 Step, Vanguard, Challenge, Verification, and Funded workflows.

`PropDayResetTimezone=UNCONFIRMED_CONSERVATIVE` is not a Trial Risk-Free micro-execution init blocker. It remains an unresolved-rule warning and still blocks protected-stage readiness until the current Upcomers reset timezone is confirmed.

Do not retry on Surge 2 Step, Vanguard, Challenge, Verification, Funded, or live-money accounts. Do not add credentials to the repo.

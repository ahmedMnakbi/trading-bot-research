# End-To-End Smoke

The non-live smoke workflow runs:

1. Config validation.
2. Deterministic fixture data generation.
3. Fixture data inspection.
4. Fixture backtest artifact creation.
5. Fixture validation artifact creation.
6. Fixture campaign artifact creation.
7. Fixture portfolio paper artifact creation.
8. Fixture portfolio report artifact creation.
9. Failure scenario.
10. Incident replay fixture.
11. Safety audit fixture.
12. Artifact registry.
13. Archive creation.

Outputs are written under `data/processed/release_checks/{release_check_id}`. Failures are captured in `failures.json` and stop the workflow cleanly.

Fixture data is used so the workflow requires no internet access and no exchange calls.

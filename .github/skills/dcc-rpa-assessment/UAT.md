# UAT: dcc-rpa-assessment

## Scenario
Given a feature page or page tree with DCC-relevant evidence, produce a merged CSV plan with the expected schema.

## Steps
1. Run the local skeleton with `--source` and `--dry-run`.
2. Confirm the printed plan includes the fixed first five DCC columns.
3. Confirm the processing fields include collection, storage, transmission, backend usage, and gap notes.
4. Confirm no write or publish action occurs in dry-run mode.

## Expected Result
- The command exits successfully.
- The output shows the expected schema and a dry-run status.

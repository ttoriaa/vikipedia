# UAT: pia-measures-bank-assessment

## Scenario
Given feature evidence and a local Measures Bank snapshot, generate a dry-run plan for the final English output table.

## Steps
1. Run the skeleton with `--source`, `--snapshot`, and `--dry-run`.
2. Confirm the plan references the snapshot file instead of live mutable content.
3. Confirm the output format is an English fixed-width HTML table.

## Expected Result
- The command exits successfully.
- The output states that the first four columns come from the snapshot source of truth.

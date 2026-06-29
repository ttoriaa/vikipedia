# UAT: confluence-update

## Scenario
Generate a dry-run update plan for a Confluence page without performing any mutation.

## Steps
1. Run the skeleton with `--instance`, `--page-id`, `--action preview`, and `--dry-run`.
2. Confirm the output includes target page, intended action, and dry-run status.
3. Confirm no update call is executed.

## Expected Result
- The command exits successfully.
- The output is proposal-first and non-destructive.

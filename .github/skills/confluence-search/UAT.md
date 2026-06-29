# UAT: confluence-search

## Scenario
Run a dry-run search plan for ATC or CC Confluence and verify the query routing metadata.

## Steps
1. Set the required environment variables locally.
2. Run `search_from_confluence.py` with `--instance`, `--query`, and `--dry-run`.
3. Confirm the printed plan includes target instance, query, and scoped retrieval mode.

## Expected Result
- The command exits successfully.
- The output stays read-only and does not attempt updates.

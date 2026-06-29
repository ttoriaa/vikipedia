# Local Jira MCP Server

This server is a minimal Python MCP implementation for Jira.

Provided tools:
- `jira_test_connection`
- `jira_search_issues`
- `jira_get_issue`

## 1) Requirements

- Python virtual environment at `.venv`
- Installed packages:
  - `fastmcp`
  - `python-dotenv`
  - `requests`

## 2) Configure environment

Add the following to `.env` in workspace root:

```env
JIRA_BASE_URL=https://atc.bmwgroup.net/jira
JIRA_EMAIL=<your-email>
JIRA_API_TOKEN=<your-api-token>
JIRA_AUTH_TYPE=auto
```

`JIRA_AUTH_TYPE` supports:
- `auto` (default): try bearer first, then basic if rejected
- `bearer`
- `basic`

## 3) Start server in VS Code

1. Run `MCP: List Servers`.
2. Select `jira`.
3. Choose `Start` (or `Restart`).

## 4) Quick verification prompt

Ask in Chat:

"Use the jira_test_connection tool"

If the call returns status `ok`, MCP wiring is working.

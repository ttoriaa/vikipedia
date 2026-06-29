# Local Confluence MCP Server

This server is a minimal Python MCP implementation for Confluence Cloud.

Provided tools:
- `confluence_test_connection`
- `confluence_search_pages`
- `confluence_get_page`
- `confluence_update_page`
- `confluence_replace_text_in_page`

## 1) Requirements

- Python virtual environment at `.venv`
- Installed packages:
  - `fastmcp`
  - `python-dotenv`
  - `requests`

## 2) Create Atlassian API token

1. Open Atlassian account security settings.
2. Create an API token.
3. Keep your Atlassian account email and Confluence base URL ready.

The update tools require Confluence credentials with page edit permission.

## 3) Configure environment

Add the following to `.env` in workspace root:

```env
CONFLUENCE_BASE_URL=https://<your-domain>.atlassian.net/wiki
CONFLUENCE_EMAIL=<your-email>
CONFLUENCE_API_TOKEN=<your-api-token>
CONFLUENCE_AUTH_TYPE=auto
```

`CONFLUENCE_AUTH_TYPE` supports:
- `auto` (default): try bearer first, then basic if rejected
- `bearer`
- `basic`

## 4) Start server in VS Code

1. Run `MCP: List Servers`.
2. Select `confluence`.
3. Choose `Start` (or `Restart`).

## 5) Quick verification prompt

Ask in Chat:

"Use the confluence_test_connection tool"

If the call returns status `ok`, MCP wiring is working.

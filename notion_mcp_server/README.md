# Local Notion MCP Server

This server is a minimal Python MCP implementation for Notion with 3 tools:

- `notion_search_pages`
- `notion_get_page_blocks`
- `notion_append_text`

## 1) Requirements

- Python virtual environment at `.venv` (already present in this workspace)
- Installed packages:
  - `fastmcp`
  - `notion-client`
  - `python-dotenv`

## 2) Create Notion integration token

1. Open Notion integration settings and create an internal integration.
2. Copy the token.
3. Share target pages with this integration in Notion.

## 3) Configure environment

Copy `.env.example` to `.env` in the workspace root and fill your token:

```env
NOTION_TOKEN=secret_xxx
```

## 4) Start server in VS Code

The workspace MCP config is already wired in `.vscode/mcp.json`.

In VS Code:

1. Run `MCP: List Servers`.
2. Select `notion`.
3. Choose `Start` (or `Restart`).
4. Confirm trust prompt when asked.

## 5) Quick verification prompt

Ask in Chat:

"Use the notion_search_pages tool to find pages with keyword: test"

If it returns results, MCP wiring is working.
# Feishu MCP Server Placeholder

This folder is reserved for your self-built Feishu MCP server.

Expected entrypoint path used by workspace MCP config:

- `feishu_mcp_server/server.py`

Required environment variables (see `.env.example`):

- `FEISHU_BASE_URL`
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_DEFAULT_DOC_TOKEN`
- `FEISHU_TIMEOUT_SECONDS`

Once `server.py` is implemented, VS Code can start the `feishu` MCP server from `.vscode/mcp.json`.

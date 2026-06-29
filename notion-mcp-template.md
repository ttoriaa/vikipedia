# Notion MCP Template

This workspace does not have a Notion MCP server configured yet. Use this as a starter template when you are ready to connect one.

## Suggested VS Code workspace config

```json
{
  "servers": {
    "notion": {
      "type": "stdio",
      "command": "<replace-with-notion-mcp-command>",
      "cwd": "${workspaceFolder}",
      "args": [
        "<replace-with-server-entrypoint-or-args>"
      ]
    }
  }
}
```

## What to replace

- `command`: the executable used to start your Notion MCP server
- `args`: the server entrypoint or startup arguments
- `cwd`: usually the workspace folder unless your server lives elsewhere

## Notes

- Keep the server name short and stable, such as `notion`.
- If your server needs environment variables, define them in the VS Code MCP configuration you use.
- Once the server exists, update the custom agent to point at that server explicitly.
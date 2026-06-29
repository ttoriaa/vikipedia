# Local Microsoft Graph MCP Server

This server provides Outlook + OneDrive access through Microsoft Graph.

Provided tools:
- `graph_test_connection`
- `outlook_list_messages`
- `outlook_get_message`
- `onedrive_list_children`
- `onedrive_get_item`

## 1) Requirements

- Python virtual environment at `.venv`
- Installed packages:
  - `fastmcp`
  - `python-dotenv`
  - `requests`
  - `msal`

## 2) Azure app setup (once)

Create an Entra ID app registration (Public client) and grant delegated permissions:
- `User.Read`
- `Mail.Read`
- `Files.Read`
- `offline_access`

Then copy the app client id.

## 3) Environment config

Add to `.env`:

```env
MSGRAPH_CLIENT_ID=<your-app-client-id>
MSGRAPH_TENANT_ID=common
MSGRAPH_SCOPES=User.Read,Mail.Read,Files.Read,offline_access
MSGRAPH_TOKEN_CACHE_PATH=.msgraph_token_cache.json
```

Optional direct token mode:

```env
MSGRAPH_ACCESS_TOKEN=<bearer-token>
```

## 4) Start server in VS Code

1. Run `MCP: List Servers`.
2. Select `msgraph`.
3. Choose `Start` (or `Restart`).

## 5) Quick verification prompt

Ask in Chat:

"Use the graph_test_connection tool"

First run may require device-code sign-in in terminal/browser.

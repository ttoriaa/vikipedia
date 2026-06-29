from __future__ import annotations

import json
import os
import pathlib
from typing import Any

import msal
import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("msgraph-local")


DEFAULT_SCOPES = [
    "User.Read",
    "Mail.Read",
    "Files.Read",
    "offline_access",
]


def _cache_path() -> pathlib.Path:
    raw = os.getenv("MSGRAPH_TOKEN_CACHE_PATH", ".msgraph_token_cache.json").strip()
    return pathlib.Path(raw)


def _authority() -> str:
    tenant = os.getenv("MSGRAPH_TENANT_ID", "common").strip() or "common"
    return f"https://login.microsoftonline.com/{tenant}"


def _client_id() -> str:
    value = os.getenv("MSGRAPH_CLIENT_ID", "").strip()
    if not value:
        raise RuntimeError(
            "MSGRAPH_CLIENT_ID is not set. Provide an Azure AD App (Public client) client id in .env."
        )
    return value


def _scopes() -> list[str]:
    raw = os.getenv("MSGRAPH_SCOPES", "").strip()
    if not raw:
        return DEFAULT_SCOPES
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return values or DEFAULT_SCOPES


def _build_app() -> tuple[msal.PublicClientApplication, msal.SerializableTokenCache]:
    cache = msal.SerializableTokenCache()
    path = _cache_path()
    if path.exists():
        cache.deserialize(path.read_text(encoding="utf-8"))

    app = msal.PublicClientApplication(
        client_id=_client_id(),
        authority=_authority(),
        token_cache=cache,
    )
    return app, cache


def _save_cache(cache: msal.SerializableTokenCache) -> None:
    if cache.has_state_changed:
        path = _cache_path()
        path.write_text(cache.serialize(), encoding="utf-8")


def _token() -> str:
    # Priority 1: explicit bearer token in env, useful for CI or quick tests.
    direct = os.getenv("MSGRAPH_ACCESS_TOKEN", "").strip()
    if direct:
        return direct

    app, cache = _build_app()
    scopes = _scopes()

    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])
        if isinstance(result, dict) and result.get("access_token"):
            _save_cache(cache)
            return str(result["access_token"])

    flow = app.initiate_device_flow(scopes=scopes)
    if "user_code" not in flow:
        raise RuntimeError(f"Failed to create device flow: {json.dumps(flow)}")

    print(flow.get("message", "Open the verification URL and enter the device code."))
    result = app.acquire_token_by_device_flow(flow)

    if not isinstance(result, dict) or "access_token" not in result:
        raise RuntimeError(f"Graph authentication failed: {json.dumps(result)}")

    _save_cache(cache)
    return str(result["access_token"])


def _graph_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    base = "https://graph.microsoft.com/v1.0"
    token = _token()
    response = requests.get(
        f"{base}{path}",
        params=params,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        timeout=30,
    )

    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Microsoft Graph error {response.status_code}: {detail}")

    return response.json()


@mcp.tool
def graph_test_connection() -> dict[str, str]:
    """Validate Graph auth and return current user profile."""
    data = _graph_get("/me")
    return {
        "status": "ok",
        "id": str(data.get("id", "")),
        "displayName": str(data.get("displayName", "")),
        "mail": str(data.get("mail", "") or data.get("userPrincipalName", "")),
    }


@mcp.tool
def outlook_list_messages(folder: str = "Inbox", limit: int = 10) -> list[dict[str, str]]:
    """List recent messages from an Outlook mail folder."""
    limit = max(1, min(limit, 50))
    data = _graph_get(
        f"/me/mailFolders/{folder}/messages",
        params={
            "$top": limit,
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,receivedDateTime,isRead,webLink",
        },
    )

    rows: list[dict[str, str]] = []
    for item in data.get("value", []):
        sender = ""
        from_payload = item.get("from", {}) if isinstance(item.get("from", {}), dict) else {}
        addr = from_payload.get("emailAddress", {}) if isinstance(from_payload.get("emailAddress", {}), dict) else {}
        sender = str(addr.get("address", ""))

        rows.append(
            {
                "id": str(item.get("id", "")),
                "subject": str(item.get("subject", "")),
                "from": sender,
                "receivedDateTime": str(item.get("receivedDateTime", "")),
                "isRead": str(item.get("isRead", "")),
                "webLink": str(item.get("webLink", "")),
            }
        )
    return rows


@mcp.tool
def outlook_get_message(message_id: str) -> dict[str, str]:
    """Get one Outlook message details by id."""
    data = _graph_get(
        f"/me/messages/{message_id}",
        params={"$select": "id,subject,bodyPreview,receivedDateTime,from,toRecipients,webLink"},
    )

    from_payload = data.get("from", {}) if isinstance(data.get("from", {}), dict) else {}
    from_email = (
        from_payload.get("emailAddress", {}) if isinstance(from_payload.get("emailAddress", {}), dict) else {}
    )

    return {
        "id": str(data.get("id", "")),
        "subject": str(data.get("subject", "")),
        "from": str(from_email.get("address", "")),
        "receivedDateTime": str(data.get("receivedDateTime", "")),
        "bodyPreview": str(data.get("bodyPreview", "")),
        "webLink": str(data.get("webLink", "")),
    }


def _drive_path(path: str) -> str:
    clean = path.strip().strip("/")
    if not clean or clean == "root":
        return "/me/drive/root/children"
    return f"/me/drive/root:/{clean}:/children"


@mcp.tool
def onedrive_list_children(path: str = "root", limit: int = 30) -> list[dict[str, str]]:
    """List files/folders from OneDrive root or sub-path."""
    limit = max(1, min(limit, 200))
    data = _graph_get(
        _drive_path(path),
        params={"$top": limit, "$select": "id,name,webUrl,size,file,folder,lastModifiedDateTime"},
    )

    rows: list[dict[str, str]] = []
    for item in data.get("value", []):
        item_type = "folder" if isinstance(item.get("folder"), dict) else "file"
        rows.append(
            {
                "id": str(item.get("id", "")),
                "name": str(item.get("name", "")),
                "type": item_type,
                "size": str(item.get("size", "")),
                "lastModifiedDateTime": str(item.get("lastModifiedDateTime", "")),
                "webUrl": str(item.get("webUrl", "")),
            }
        )
    return rows


@mcp.tool
def onedrive_get_item(item_id: str) -> dict[str, str]:
    """Get OneDrive file/folder metadata by item id."""
    data = _graph_get(
        f"/me/drive/items/{item_id}",
        params={"$select": "id,name,webUrl,size,file,folder,lastModifiedDateTime,parentReference"},
    )

    item_type = "folder" if isinstance(data.get("folder"), dict) else "file"
    parent = data.get("parentReference", {}) if isinstance(data.get("parentReference", {}), dict) else {}

    return {
        "id": str(data.get("id", "")),
        "name": str(data.get("name", "")),
        "type": item_type,
        "size": str(data.get("size", "")),
        "lastModifiedDateTime": str(data.get("lastModifiedDateTime", "")),
        "parentPath": str(parent.get("path", "")),
        "webUrl": str(data.get("webUrl", "")),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")

from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("confluence-local")


def _config() -> tuple[str, str, str]:
    base_url = os.getenv("CONFLUENCE_BASE_URL", "").strip().rstrip("/")
    email = os.getenv("CONFLUENCE_EMAIL", "").strip()
    api_token = os.getenv("CONFLUENCE_API_TOKEN", "").strip()

    if not base_url or not email or not api_token:
        raise RuntimeError(
            "Missing Confluence credentials. Set CONFLUENCE_BASE_URL, CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN in .env"
        )

    return base_url, email, api_token


def _request_once(
    base_url: str,
    email: str,
    api_token: str,
    method: str,
    path: str,
    params: dict[str, Any] | None,
    json_body: dict[str, Any] | None,
    auth_mode: str,
) -> requests.Response:
    url = f"{base_url}{path}"
    headers = {"Accept": "application/json"}
    kwargs: dict[str, Any] = {
        "params": params,
        "json": json_body,
        "headers": headers,
        "timeout": 20,
    }

    if auth_mode == "basic":
        kwargs["auth"] = (email, api_token)
    elif auth_mode == "bearer":
        headers["Authorization"] = f"Bearer {api_token}"
    else:
        raise ValueError(f"Unsupported auth mode: {auth_mode}")

    return requests.request(method, url, **kwargs)


def _request(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    base_url, email, api_token = _config()
    auth_type = os.getenv("CONFLUENCE_AUTH_TYPE", "auto").strip().lower()

    if auth_type == "auto":
        # Many enterprise Confluence setups use bearer tokens; fall back to basic when rejected.
        first = _request_once(base_url, email, api_token, "GET", path, params, None, "bearer")
        if first.status_code in (401, 403):
            response = _request_once(base_url, email, api_token, "GET", path, params, None, "basic")
        else:
            response = first
    elif auth_type in {"basic", "bearer"}:
        response = _request_once(base_url, email, api_token, "GET", path, params, None, auth_type)
    else:
        raise RuntimeError("CONFLUENCE_AUTH_TYPE must be one of: auto, basic, bearer")

    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Confluence API error {response.status_code}: {detail}")

    return response.json()


def _request_write(path: str, json_body: dict[str, Any]) -> dict[str, Any]:
    base_url, email, api_token = _config()
    auth_type = os.getenv("CONFLUENCE_AUTH_TYPE", "auto").strip().lower()

    if auth_type == "auto":
        first = _request_once(base_url, email, api_token, "PUT", path, None, json_body, "bearer")
        if first.status_code in (401, 403):
            response = _request_once(base_url, email, api_token, "PUT", path, None, json_body, "basic")
        else:
            response = first
    elif auth_type in {"basic", "bearer"}:
        response = _request_once(base_url, email, api_token, "PUT", path, None, json_body, auth_type)
    else:
        raise RuntimeError("CONFLUENCE_AUTH_TYPE must be one of: auto, basic, bearer")

    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Confluence API error {response.status_code}: {detail}")

    if response.text.strip():
        return response.json()
    return {}


@mcp.tool
def confluence_test_connection() -> dict[str, str]:
    """Validate Confluence credentials and return site metadata."""
    info = _request("/rest/api/space", params={"limit": 1})
    first_space = ""
    if isinstance(info.get("results", []), list) and info.get("results"):
        first = info.get("results", [])[0]
        if isinstance(first, dict):
            first_space = str(first.get("key", ""))

    return {
        "baseUrl": _config()[0],
        "status": "ok",
        "firstSpaceKey": first_space,
    }


@mcp.tool
def confluence_search_pages(query: str, limit: int = 10) -> list[dict[str, str]]:
    """Search Confluence pages by CQL text."""
    limit = max(1, min(limit, 50))
    result = _request(
        "/rest/api/search",
        params={"cql": f'type = "page" and text ~ "{query}"', "limit": limit},
    )

    rows: list[dict[str, str]] = []
    for item in result.get("results", []):
        content = item.get("content", {}) if isinstance(item.get("content", {}), dict) else {}
        rows.append(
            {
                "id": str(content.get("id", "")),
                "title": str(content.get("title", "")),
                "type": str(content.get("type", "")),
                "status": str(content.get("status", "")),
                "url": str(item.get("url", "")),
            }
        )
    return rows


@mcp.tool
def confluence_get_page(page_id: str) -> dict[str, str]:
    """Get page title and body (storage format) by page id."""
    result = _request(
        f"/rest/api/content/{page_id}",
        params={"expand": "body.storage,space,version"},
    )

    body = (
        result.get("body", {})
        .get("storage", {})
        .get("value", "")
        if isinstance(result.get("body", {}), dict)
        else ""
    )

    return {
        "id": str(result.get("id", "")),
        "title": str(result.get("title", "")),
        "space": str(result.get("space", {}).get("key", "")) if isinstance(result.get("space", {}), dict) else "",
        "version": str(result.get("version", {}).get("number", "")) if isinstance(result.get("version", {}), dict) else "",
        "body_storage": str(body),
    }


@mcp.tool
def confluence_update_page(page_id: str, body_storage: str, title: str = "") -> dict[str, str]:
    """Update a Confluence page body in storage format."""
    page_id = page_id.strip()
    if not page_id:
        raise ValueError("page_id must not be empty")

    current = confluence_get_page(page_id)
    current_title = title.strip() or current.get("title", "")
    current_version_raw = current.get("version", "0")

    try:
        current_version = int(str(current_version_raw))
    except Exception:
        current_version = 0

    payload = {
        "id": page_id,
        "type": "page",
        "title": current_title,
        "version": {"number": current_version + 1},
        "body": {"storage": {"value": body_storage, "representation": "storage"}},
    }

    result = _request_write(f"/rest/api/content/{page_id}", payload)
    updated_version = result.get("version", {}).get("number", current_version + 1) if isinstance(result.get("version", {}), dict) else current_version + 1
    return {
        "status": "ok",
        "id": str(result.get("id", page_id)),
        "title": str(result.get("title", current_title)),
        "version": str(updated_version),
    }


@mcp.tool
def confluence_replace_text_in_page(page_id: str, old_text: str, new_text: str) -> dict[str, str]:
    """Replace text in a single Confluence page body and save the updated page."""
    page_id = page_id.strip()
    if not page_id:
        raise ValueError("page_id must not be empty")
    if not old_text:
        raise ValueError("old_text must not be empty")

    current = confluence_get_page(page_id)
    body_storage = current.get("body_storage", "")
    if old_text not in body_storage:
        return {
            "status": "noop",
            "id": page_id,
            "title": current.get("title", ""),
            "reason": f"'{old_text}' not found in page body",
        }

    updated_body = body_storage.replace(old_text, new_text)
    result = confluence_update_page(page_id=page_id, body_storage=updated_body, title=current.get("title", ""))
    return {
        "status": result.get("status", "ok"),
        "id": result.get("id", page_id),
        "title": result.get("title", current.get("title", "")),
        "version": result.get("version", ""),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")

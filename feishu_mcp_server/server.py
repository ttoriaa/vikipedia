from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("feishu-local")


def _config() -> tuple[str, str, str, int]:
    base_url = os.getenv("FEISHU_BASE_URL", "https://open.feishu.cn").strip().rstrip("/")
    app_id = os.getenv("FEISHU_APP_ID", "").strip()
    app_secret = os.getenv("FEISHU_APP_SECRET", "").strip()
    timeout_raw = os.getenv("FEISHU_TIMEOUT_SECONDS", "30").strip()

    if not app_id or not app_secret:
        raise RuntimeError(
            "Missing Feishu credentials. Set FEISHU_APP_ID and FEISHU_APP_SECRET in .env"
        )

    try:
        timeout_seconds = int(timeout_raw)
    except Exception:
        timeout_seconds = 30

    return base_url, app_id, app_secret, max(5, min(timeout_seconds, 120))


def _default_doc_token() -> str:
    return os.getenv("FEISHU_DEFAULT_DOC_TOKEN", "").strip()


def _default_parent_block_id() -> str:
    return os.getenv("FEISHU_DEFAULT_PARENT_BLOCK_ID", "").strip()


def _tenant_access_token() -> str:
    base_url, app_id, app_secret, timeout_seconds = _config()
    url = f"{base_url}/open-apis/auth/v3/tenant_access_token/internal"

    response = requests.post(
        url,
        json={"app_id": app_id, "app_secret": app_secret},
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=timeout_seconds,
    )

    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Feishu auth HTTP error {response.status_code}: {detail}")

    payload = response.json()
    code = int(payload.get("code", -1))
    if code != 0:
        raise RuntimeError(f"Feishu auth API error {code}: {payload.get('msg', '')}")

    token = str(payload.get("tenant_access_token", "")).strip()
    if not token:
        raise RuntimeError("Feishu auth succeeded but no tenant_access_token was returned.")

    return token


def _request(
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_url, _, _, timeout_seconds = _config()
    token = _tenant_access_token()

    response = requests.request(
        method=method,
        url=f"{base_url}{path}",
        params=params,
        json=json_body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        timeout=timeout_seconds,
    )

    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Feishu API HTTP error {response.status_code}: {detail}")

    payload = response.json()
    code = int(payload.get("code", -1))
    if code != 0:
        raise RuntimeError(f"Feishu API error {code}: {payload.get('msg', '')}")

    return payload


@mcp.tool
def feishu_test_connection() -> dict[str, str]:
    """Validate Feishu app credentials by requesting tenant access token."""
    token = _tenant_access_token()
    base_url, app_id, _, _ = _config()
    return {
        "status": "ok",
        "baseUrl": base_url,
        "appId": app_id,
        "tokenPreview": f"{token[:8]}...",
    }


@mcp.tool
def feishu_get_doc(document_id: str) -> dict[str, str]:
    """Get Feishu doc metadata by document id (doc token)."""
    document_id = document_id.strip()
    if not document_id:
        raise ValueError("document_id must not be empty")

    payload = _request("GET", f"/open-apis/docx/v1/documents/{document_id}")
    data = payload.get("data", {}) if isinstance(payload.get("data", {}), dict) else {}
    document = data.get("document", {}) if isinstance(data.get("document", {}), dict) else {}

    return {
        "document_id": str(document.get("document_id", document_id)),
        "title": str(document.get("title", "")),
        "revision_id": str(document.get("revision_id", "")),
    }


@mcp.tool
def feishu_append_text(
    text: str,
    document_id: str = "",
    parent_block_id: str = "",
) -> dict[str, str]:
    """Append text paragraphs under a parent block in a Feishu doc.

    Notes:
    - `document_id` is the Feishu doc token. If omitted, FEISHU_DEFAULT_DOC_TOKEN is used.
    - `parent_block_id` is optional. If omitted, FEISHU_DEFAULT_PARENT_BLOCK_ID is used.
    - If neither is set, the tool falls back to the document root block.
    - Each non-empty line in `text` becomes a paragraph block.
    """
    document_id = document_id.strip() or _default_doc_token()
    parent_block_id = parent_block_id.strip() or _default_parent_block_id()

    if not document_id:
        raise ValueError(
            "document_id must not be empty. Pass document_id or set FEISHU_DEFAULT_DOC_TOKEN in .env"
        )
    if not parent_block_id:
        parent_block_id = document_id

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return {"status": "noop", "reason": "No non-empty lines to append."}

    children: list[dict[str, Any]] = []
    for line in lines[:100]:
        children.append(
            {
                "block_type": 2,
                "paragraph": {
                    "elements": [
                        {
                            "text_run": {"content": line},
                        }
                    ]
                },
            }
        )

    payload = _request(
        "POST",
        f"/open-apis/docx/v1/documents/{document_id}/blocks/{parent_block_id}/children",
        json_body={"children": children},
    )

    data = payload.get("data", {}) if isinstance(payload.get("data", {}), dict) else {}
    children_data = data.get("children", []) if isinstance(data.get("children", []), list) else []

    return {
        "status": "ok",
        "document_id": document_id,
        "parent_block_id": parent_block_id,
        "appended_blocks": str(len(children_data) if children_data else len(children)),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")

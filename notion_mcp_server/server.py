from __future__ import annotations

import re
from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP
from notion_client import Client

load_dotenv()

mcp = FastMCP("notion-local")


def _client() -> Client:
    import os

    token = os.getenv("NOTION_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "NOTION_TOKEN is not set. Create a .env file in the workspace with NOTION_TOKEN=<your token>."
        )
    return Client(auth=token)


def _to_uuid(page_id_or_url: str) -> str:
    text = page_id_or_url.strip()

    # Accept plain 32-hex, UUID, or Notion URL containing a 32-hex page id.
    direct_uuid = re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", text
    )
    if direct_uuid:
        return text.lower()

    hex_match = re.search(r"[0-9a-fA-F]{32}", text.replace("-", ""))
    if not hex_match:
        raise ValueError(
            "Invalid page id or URL. Expected a Notion page URL, UUID, or 32-char hex id."
        )

    value = hex_match.group(0).lower()
    return f"{value[0:8]}-{value[8:12]}-{value[12:16]}-{value[16:20]}-{value[20:32]}"


def _rich_text_to_plain(chunks: list[dict[str, Any]]) -> str:
    return "".join(str(c.get("plain_text", "")) for c in chunks)


def _extract_page_title(page: dict[str, Any]) -> str:
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            return _rich_text_to_plain(prop.get("title", [])) or "Untitled"
    return "Untitled"


def _line_to_block(line: str) -> dict[str, Any]:
    if line.startswith("### "):
        return {
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
            },
        }
    if line.startswith("## "):
        return {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
            },
        }
    if line.startswith("# "):
        return {
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
            },
        }
    if line.startswith("- "):
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
            },
        }
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]},
    }


@mcp.tool
def notion_search_pages(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Search accessible Notion pages by query string."""
    limit = max(1, min(limit, 20))
    notion = _client()
    result = notion.search(
        query=query,
        filter={"property": "object", "value": "page"},
        page_size=limit,
    )

    pages: list[dict[str, str]] = []
    for page in result.get("results", []):
        if page.get("object") != "page":
            continue
        pages.append(
            {
                "id": str(page.get("id", "")),
                "title": _extract_page_title(page),
                "url": str(page.get("url", "")),
                "last_edited_time": str(page.get("last_edited_time", "")),
            }
        )
    return pages


@mcp.tool
def notion_get_page_blocks(page_id_or_url: str, page_size: int = 50) -> list[dict[str, str]]:
    """Read top-level blocks from a Notion page."""
    notion = _client()
    page_id = _to_uuid(page_id_or_url)
    page_size = max(1, min(page_size, 100))

    result = notion.blocks.children.list(block_id=page_id, page_size=page_size)
    blocks: list[dict[str, str]] = []

    for block in result.get("results", []):
        block_type = str(block.get("type", "unknown"))
        payload = block.get(block_type, {}) if isinstance(block.get(block_type, {}), dict) else {}
        text = _rich_text_to_plain(payload.get("rich_text", []))
        blocks.append(
            {
                "id": str(block.get("id", "")),
                "type": block_type,
                "text": text,
            }
        )
    return blocks


@mcp.tool
def notion_append_text(page_id_or_url: str, text: str) -> dict[str, str]:
    """Append plain text/markdown-like lines to a Notion page.

    Supported prefixes:
    - '# ', '## ', '### ' for headings
    - '- ' for bullet items
    - other lines become paragraphs
    """
    notion = _client()
    page_id = _to_uuid(page_id_or_url)

    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if not lines:
        return {"status": "noop", "reason": "No non-empty lines to append."}

    children = [_line_to_block(line) for line in lines[:100]]
    notion.blocks.children.append(block_id=page_id, children=children)
    return {"status": "ok", "appended_blocks": str(len(children))}


if __name__ == "__main__":
    mcp.run(transport="stdio")
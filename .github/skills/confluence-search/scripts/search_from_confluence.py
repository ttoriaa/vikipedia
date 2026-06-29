from __future__ import annotations

import argparse
import json

from confluence_direct_client import ConfluenceDirectClient
from confluence_api import extract_page_id, strip_storage_html


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search or retrieve Confluence content from CC or ATC")
    parser.add_argument("--instance", choices=["atc", "cc"], required=True)
    parser.add_argument("--mode", choices=["auto", "keyword", "cql", "page", "page-tree"], default="auto")
    parser.add_argument("--query", help="Keyword query for text search")
    parser.add_argument("--cql", help="Raw CQL query")
    parser.add_argument("--page-ref", help="Numeric page id or page URL")
    parser.add_argument("--space-key", help="Optional space key scope for keyword search")
    parser.add_argument("--ancestor", help="Optional ancestor page id or URL for keyword search")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--max-depth", type=int, default=1)
    parser.add_argument("--include-body", action="store_true", help="Include stripped page body for page retrieval")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def resolve_mode(args: argparse.Namespace) -> str:
    if args.mode != "auto":
        return args.mode
    if args.cql:
        return "cql"
    if args.page_ref:
        return "page"
    return "keyword"


def result_row(client: ConfluenceDirectClient, item: dict) -> dict:
    content = item.get("content", {}) if isinstance(item.get("content", {}), dict) else item
    title = str(content.get("title", item.get("title", "")))
    page_id = str(content.get("id", item.get("id", "")))
    excerpt = str(item.get("excerpt", "")).replace("<em>", "").replace("</em>", "")
    return {
        "id": page_id,
        "title": title,
        "url": client.page_webui_url(content if isinstance(content, dict) else item),
        "excerpt": excerpt,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    mode = resolve_mode(args)
    client = ConfluenceDirectClient.for_instance(args.instance)
    ancestor_id = extract_page_id(args.ancestor) if args.ancestor else None
    plan = {
        "skill": "confluence-search",
        "client": client.describe(),
        "mode": mode,
        "query": args.query,
        "cql": args.cql,
        "page_ref": args.page_ref,
        "space_key": args.space_key,
        "ancestor": ancestor_id,
        "limit": args.limit,
        "max_depth": args.max_depth,
        "include_body": args.include_body,
        "dry_run": args.dry_run,
    }
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=True, indent=2))
        return 0

    if mode == "keyword":
        if not args.query:
            raise SystemExit("--query is required for keyword mode")
        results = client.search_keyword(args.query, limit=args.limit, space_key=args.space_key, ancestor_id=ancestor_id)
        payload = {"mode": mode, "count": len(results), "results": [result_row(client, item) for item in results]}
    elif mode == "cql":
        if not args.cql:
            raise SystemExit("--cql is required for cql mode")
        results = client.search_cql(args.cql, limit=args.limit)
        payload = {"mode": mode, "count": len(results), "results": [result_row(client, item) for item in results]}
    elif mode == "page-tree":
        if not args.page_ref:
            raise SystemExit("--page-ref is required for page-tree mode")
        tree = client.walk_page_tree(args.page_ref, max_depth=max(0, args.max_depth))
        payload = {"mode": mode, "count": len(tree), "results": tree}
    else:
        if not args.page_ref:
            raise SystemExit("--page-ref is required for page mode")
        page = client.get_page(args.page_ref)
        payload = {
            "mode": mode,
            "id": str(page.get("id", "")),
            "title": str(page.get("title", "")),
            "url": client.page_webui_url(page),
            "version": int(((page.get("version") or {}).get("number")) or 0),
        }
        if args.include_body:
            body = str((((page.get("body") or {}).get("storage") or {}).get("value")) or "")
            payload["body_text"] = strip_storage_html(body)
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

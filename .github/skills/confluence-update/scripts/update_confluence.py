from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from confluence_api import ConfluenceClient, strip_storage_html  # noqa: E402


def read_optional_text(file_path: str | None, inline_text: str | None) -> str | None:
    if file_path:
        return Path(file_path).read_text(encoding="utf-8")
    if inline_text is not None:
        return inline_text
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview or apply controlled Confluence page updates")
    parser.add_argument("--instance", choices=["atc", "cc"], required=True)
    parser.add_argument("--page-ref", required=True, help="Numeric page id or full Confluence page URL")
    parser.add_argument("--title", help="Optional replacement title")
    parser.add_argument("--body-file", help="Replace page body from a file")
    parser.add_argument("--body-text", help="Replace page body from an inline string")
    parser.add_argument("--append-file", help="Append body content from a file")
    parser.add_argument("--append-text", help="Append body content from an inline string")
    parser.add_argument("--replace-old", help="Existing text to replace")
    parser.add_argument("--replace-new", default="", help="Replacement text for --replace-old")
    parser.add_argument("--output-body-file", help="Write the proposed body to a local file")
    parser.add_argument("--apply", action="store_true", help="Execute the update instead of preview only")
    args = parser.parse_args()

    client = ConfluenceClient.for_instance(args.instance)
    current = client.get_page(args.page_ref)
    current_body = str((((current.get("body") or {}).get("storage") or {}).get("value")) or "")
    next_title = args.title or str(current.get("title", ""))
    proposed_body = current_body

    replacement_body = read_optional_text(args.body_file, args.body_text)
    append_body = read_optional_text(args.append_file, args.append_text)

    action = "preview"
    if replacement_body is not None:
        proposed_body = replacement_body
        action = "set-body"
    if append_body is not None:
        proposed_body = proposed_body + append_body
        action = "append-body"
    if args.replace_old is not None:
        proposed_body = proposed_body.replace(args.replace_old, args.replace_new)
        action = "replace-text"

    changed = proposed_body != current_body or next_title != str(current.get("title", ""))
    payload = {
        "skill": "confluence-update",
        "instance": args.instance,
        "page_id": str(current.get("id", "")),
        "title": next_title,
        "action": action,
        "apply": args.apply,
        "changed": changed,
        "current_version": int(((current.get("version") or {}).get("number")) or 0),
        "current_title": str(current.get("title", "")),
        "current_excerpt": strip_storage_html(current_body)[:280],
        "proposed_excerpt": strip_storage_html(proposed_body)[:280],
        "url": client.page_webui_url(current),
    }

    if args.output_body_file:
        Path(args.output_body_file).write_text(proposed_body, encoding="utf-8")
        payload["output_body_file"] = args.output_body_file

    if not args.apply:
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        return 0

    if not changed:
        payload["status"] = "noop"
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        return 0

    updated = client.update_page(args.page_ref, title=next_title, body_storage=proposed_body)
    payload["status"] = "ok"
    payload["updated_id"] = str(updated.get("id", ""))
    payload["updated_title"] = str(updated.get("title", next_title))
    payload["updated_version"] = int(((updated.get("version") or {}).get("number")) or 0)
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

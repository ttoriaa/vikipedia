from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from jira_api import JiraClient  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview or apply controlled Jira issue updates")
    parser.add_argument("--issue", required=True, help="Issue key, for example SECMGTCN-123")
    parser.add_argument("--intent", required=True, help="Human-readable change intent")
    parser.add_argument("--summary", help="Replace issue summary")
    parser.add_argument("--description", help="Replace issue description with inline text")
    parser.add_argument("--description-file", help="Replace issue description from file")
    parser.add_argument("--comment", help="Append one Jira comment")
    parser.add_argument("--comment-file", help="Append one Jira comment from file")
    parser.add_argument("--labels-add", nargs="*", default=[])
    parser.add_argument("--labels-set", nargs="*", help="Replace labels entirely")
    parser.add_argument("--output-plan", help="Optional path to write preview JSON")
    parser.add_argument("--apply", action="store_true")
    return parser


def load_optional_text(inline_text: str | None, file_path: str | None) -> str | None:
    if file_path:
        return Path(file_path).read_text(encoding="utf-8")
    if inline_text is not None:
        return inline_text
    return None


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    client = JiraClient()
    issue = client.get_issue(args.issue)
    fields = issue.get("fields", {}) if isinstance(issue.get("fields", {}), dict) else {}
    current_labels = list(fields.get("labels", [])) if isinstance(fields.get("labels", []), list) else []

    next_fields: dict[str, object] = {}
    description = load_optional_text(args.description, args.description_file)
    comment = load_optional_text(args.comment, args.comment_file)

    if args.summary is not None:
        next_fields["summary"] = args.summary
    if description is not None:
        next_fields["description"] = description
    if args.labels_set is not None:
        next_fields["labels"] = list(args.labels_set)
    elif args.labels_add:
        next_fields["labels"] = sorted(set(current_labels).union(args.labels_add))

    preview = {
        "skill": "jira-update",
        "client": client.describe(),
        "issue": args.issue,
        "intent": args.intent,
        "apply": args.apply,
        "current": {
            "summary": str(fields.get("summary", "")),
            "status": str(((fields.get("status") or {}).get("name")) or ""),
            "labels": current_labels,
            "updated": str(fields.get("updated", "")),
        },
        "proposed_fields": next_fields,
        "comment_present": bool(comment),
        "will_change": bool(next_fields or comment),
    }

    if args.output_plan:
        Path(args.output_plan).write_text(json.dumps(preview, ensure_ascii=True, indent=2), encoding="utf-8")
        preview["output_plan"] = args.output_plan

    if not args.apply:
        print(json.dumps(preview, ensure_ascii=True, indent=2))
        return 0

    if not next_fields and not comment:
        preview["status"] = "noop"
        print(json.dumps(preview, ensure_ascii=True, indent=2))
        return 0

    results: dict[str, object] = {"issue": args.issue}
    if next_fields:
        client.update_issue_fields(args.issue, next_fields)
        results["fields_updated"] = sorted(next_fields.keys())
    if comment:
        comment_result = client.add_comment(args.issue, comment)
        results["comment_id"] = str(comment_result.get("id", ""))

    preview["status"] = "ok"
    preview["result"] = results
    print(json.dumps(preview, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

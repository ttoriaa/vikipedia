#!/usr/bin/env python3
"""Append one structured decision note into personal knowledge base notes."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def clean(value: str) -> str:
    return value.strip()


def now_local() -> datetime:
    return datetime.now()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append a structured decision log entry")
    parser.add_argument("--date", default=now_local().strftime("%Y-%m-%d"), help="Decision date YYYY-MM-DD")
    parser.add_argument("--title", required=True, help="Decision title")
    parser.add_argument("--context", default="", help="Context and trigger")
    parser.add_argument("--decision", required=True, help="Decision made")
    parser.add_argument("--rationale", default="", help="Why this decision")
    parser.add_argument("--impact", default="", help="Expected impact")
    parser.add_argument("--next", default="", help="Next action")
    parser.add_argument("--owner", default="", help="Decision owner")
    parser.add_argument("--source", default="chat", help="Source channel")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    return parser


def ensure_note_file(note_path: Path, date_value: str) -> None:
    if note_path.exists():
        return
    note_path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "# Decision Notes",
        "",
        f"- Date: {date_value}",
        "- Purpose: capture high-impact decisions from chats and implementation work.",
        "",
    ]
    note_path.write_text("\n".join(header), encoding="utf-8")


def append_markdown_entry(
    note_path: Path,
    timestamp: str,
    title: str,
    context: str,
    decision: str,
    rationale: str,
    impact: str,
    next_action: str,
    owner: str,
    source: str,
    tags: str,
) -> None:
    lines = [
        "",
        f"## [{timestamp}] {title}",
        f"- Source: {source}",
        f"- Context: {context or 'n/a'}",
        f"- Decision: {decision}",
        f"- Rationale: {rationale or 'n/a'}",
        f"- Impact: {impact or 'n/a'}",
        f"- Next: {next_action or 'n/a'}",
        f"- Owner: {owner or 'n/a'}",
        f"- Tags: {tags or 'n/a'}",
    ]
    with note_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def append_jsonl_entry(index_path: Path, payload: dict[str, str]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> None:
    args = build_parser().parse_args()

    date_value = clean(args.date) or now_local().strftime("%Y-%m-%d")

    repo_root = Path(__file__).resolve().parents[1]
    notes_root = repo_root / "reports" / "knowledge_base" / "notes"
    note_path = notes_root / f"{date_value}_decisions.md"
    index_path = notes_root / "decision_log.jsonl"

    timestamp = now_local().strftime("%H:%M:%S")
    title = clean(args.title)
    context = clean(args.context)
    decision = clean(args.decision)
    rationale = clean(args.rationale)
    impact = clean(args.impact)
    next_action = clean(args.next)
    owner = clean(args.owner)
    source = clean(args.source)
    tags = clean(args.tags)

    ensure_note_file(note_path, date_value)
    append_markdown_entry(
        note_path,
        timestamp,
        title,
        context,
        decision,
        rationale,
        impact,
        next_action,
        owner,
        source,
        tags,
    )

    append_jsonl_entry(
        index_path,
        {
            "date": date_value,
            "time": timestamp,
            "title": title,
            "context": context,
            "decision": decision,
            "rationale": rationale,
            "impact": impact,
            "next": next_action,
            "owner": owner,
            "source": source,
            "tags": tags,
            "note_file": note_path.as_posix(),
        },
    )

    print(f"Decision note appended: {note_path}")
    print(f"Decision index updated: {index_path}")


if __name__ == "__main__":
    main()

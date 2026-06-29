from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from confluence_api import ConfluenceClient, strip_storage_html


ROOT = Path(__file__).resolve().parents[1]
INDEX_START = "<!-- SKILL_BACKUP_INDEX:START -->"
INDEX_END = "<!-- SKILL_BACKUP_INDEX:END -->"


def parse_skill_markdown(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            text = parts[2]
    lines = text.splitlines()
    title = path.parent.name.replace("-", " ").title()
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return {
        "title": title,
        "purpose": "\n".join(sections.get("Purpose", [])).strip(),
        "when": "\n".join(sections.get("When To Use", [])).strip(),
        "inputs": "\n".join(sections.get("Inputs", [])).strip(),
        "outputs": "\n".join(sections.get("Outputs", [])).strip(),
        "boundaries": "\n".join(sections.get("Boundaries", [])).strip(),
        "sensitivity": "\n".join(sections.get("Sensitivity", [])).strip(),
    }


def render_text_block(text: str) -> str:
    if not text:
        return "<p>No content provided.</p>"
    chunks: list[str] = []
    list_items: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if list_items:
                chunks.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
                list_items = []
            continue
        if line.startswith("- "):
            list_items.append(html.escape(line[2:].strip()))
            continue
        if list_items:
            chunks.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items = []
        chunks.append(f"<p>{html.escape(line)}</p>")
    if list_items:
        chunks.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
    return "".join(chunks)


def infer_file_purpose(path: Path) -> str:
    if path.name == "SKILL.md":
        return "Primary skill contract and routing instructions."
    if path.name == "README.md":
        return "Setup, examples, and operational notes."
    if path.name == "UAT.md":
        return "User acceptance test scenario for expected behavior."
    if path.name == "UAT.meta.json":
        return "Structured UAT metadata."
    if path.suffix == ".py":
        return "Runtime/helper script referenced by the skill."
    if path.suffix == ".json":
        return "Reference data, fixture, or generated snapshot required by the skill."
    return "Supporting asset used by the skill package."


def collect_source_files(skill_dir: Path, slug: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for file_path in sorted(skill_dir.rglob("*")):
        if not file_path.is_file():
            continue
        if "__pycache__" in file_path.parts or file_path.suffix == ".pyc":
            continue
        rel = file_path.relative_to(ROOT).as_posix()
        rows.append((rel, infer_file_purpose(file_path)))
    if slug == "skill-backup-sync":
        rel = Path("scripts/publish_skill_backup_pages.py").as_posix()
        rows.append((rel, "Runtime/helper script referenced by the skill."))
    return rows


def render_source_files_table(rows: list[tuple[str, str]]) -> str:
    parts = ["<table><thead><tr><th>Path</th><th>Purpose</th></tr></thead><tbody>"]
    for path, purpose in rows:
        parts.append(f"<tr><td>{html.escape(path)}</td><td>{html.escape(purpose)}</td></tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def build_child_page_body(skill_dir: Path, slug: str) -> tuple[str, str, str]:
    parsed = parse_skill_markdown(skill_dir / "SKILL.md")
    display_title = parsed["title"]
    backup_title = f"Skill Backup - {display_title}"
    source_rows = collect_source_files(skill_dir, slug)
    synced_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = "".join(
        [
            f"<h1>{html.escape(display_title)}</h1>",
            "<p>Status: reusable skill backup generated from the active workspace skill set.</p>",
            "<h2>Overview</h2>",
            render_text_block(parsed["purpose"]),
            "<h2>When To Use</h2>",
            render_text_block(parsed["when"]),
            "<h2>Inputs</h2>",
            render_text_block(parsed["inputs"]),
            "<h2>Outputs</h2>",
            render_text_block(parsed["outputs"]),
            "<h2>Source Files</h2>",
            render_source_files_table(source_rows),
            "<h2>Contract Checklist</h2>",
            "<ul><li>Required section: Purpose</li><li>Required section: Inputs</li><li>Required section: Outputs</li><li>Required section: Boundaries</li></ul>",
            "<h2>Safety And Sensitivity Notes</h2>",
            render_text_block(parsed["sensitivity"] or parsed["boundaries"]),
            "<h2>Last Synced</h2>",
            f"<p>Generated from .github/skills/{html.escape(slug)}/SKILL.md on {html.escape(synced_at)}.</p>",
        ]
    )
    overview = strip_storage_html(render_text_block(parsed["purpose"])) or parsed["purpose"]
    sensitivity = parsed["sensitivity"].splitlines()[0].strip() if parsed["sensitivity"].strip() else "Not specified"
    return backup_title, body, overview or "No purpose provided"


def build_index_section(rows: list[dict[str, str]]) -> str:
    parts = [
        INDEX_START,
        "<h1>Reusable Skill Backup Index</h1>",
        "<p>This section lists the active workspace Copilot skills backed up as reusable child pages. The child pages are concise reuse guides, not full source-code dumps.</p>",
        "<table><thead><tr><th>Skill Page</th><th>Purpose</th><th>Source</th><th>Sensitivity</th></tr></thead><tbody>",
    ]
    for row in rows:
        parts.append(
            "".join(
                [
                    "<tr>",
                    f"<td><a href=\"{html.escape(row['url'])}\">{html.escape(row['title'])}</a></td>",
                    f"<td>{html.escape(row['purpose'])}</td>",
                    f"<td>{html.escape(row['source'])}</td>",
                    f"<td>{html.escape(row['sensitivity'])}</td>",
                    "</tr>",
                ]
            )
        )
    parts.append("</tbody></table>")
    parts.append(f"<p>Last refreshed: {html.escape(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))}.</p>")
    parts.append(INDEX_END)
    return "".join(parts)


def replace_or_append_section(body: str, section_html: str) -> str:
    pattern = re.compile(re.escape(INDEX_START) + r".*?" + re.escape(INDEX_END), re.DOTALL)
    if pattern.search(body):
        return pattern.sub(section_html, body)
    return body + section_html


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish local skill backup pages to Confluence")
    parser.add_argument("--instance", choices=["atc", "cc"], default="atc")
    parser.add_argument("--root-page", required=True)
    parser.add_argument("--source-dir", default=".github/skills")
    parser.add_argument("--skill", action="append", help="Optional skill slug filter; can be repeated")
    parser.add_argument("--apply", action="store_true", help="Create or update child pages and root index")
    parser.add_argument("--include-template", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    client = ConfluenceClient.for_instance(args.instance)
    root_page = client.get_page(args.root_page)
    root_space_key = str(((root_page.get("space") or {}).get("key")) or "")

    source_dir = (ROOT / args.source_dir).resolve()
    allowed = set(args.skill or [])
    skill_dirs = []
    for child in sorted(source_dir.iterdir()):
        if not child.is_dir() or not (child / "SKILL.md").exists():
            continue
        if child.name == "reusable-skill-template" and not args.include_template:
            continue
        if allowed and child.name not in allowed:
            continue
        skill_dirs.append(child)

    results: list[dict[str, str]] = []
    for skill_dir in skill_dirs:
        slug = skill_dir.name
        child_title, child_body, overview = build_child_page_body(skill_dir, slug)
        existing = client.find_child_page(args.root_page, child_title)
        action = "update" if existing else "create"
        child_url = ""
        if args.apply and not args.dry_run:
            if existing:
                updated = client.update_page(str(existing.get("id", "")), title=child_title, body_storage=child_body)
                child_url = client.page_webui_url(updated)
            else:
                created = client.create_page(space_key=root_space_key, title=child_title, body_storage=child_body, parent_page_ref=args.root_page)
                child_url = client.page_webui_url(created)
        elif existing:
            child_url = client.page_webui_url(existing)
        results.append(
            {
                "slug": slug,
                "title": child_title,
                "action": action,
                "page_id": str((existing or {}).get("id", "")),
                "url": child_url,
                "purpose": overview.splitlines()[0].strip(),
                "source": f".github/skills/{slug}/SKILL.md",
                "sensitivity": parse_skill_markdown(skill_dir / "SKILL.md")["sensitivity"].splitlines()[0].strip() or "Not specified",
            }
        )

    index_section = build_index_section(results)
    root_body = str((((root_page.get("body") or {}).get("storage") or {}).get("value")) or "")
    proposed_root_body = replace_or_append_section(root_body, index_section)

    if args.apply and not args.dry_run:
        client.update_page(args.root_page, title=str(root_page.get("title", "")), body_storage=proposed_root_body)

    print(
        json.dumps(
            {
                "skill": "skill-backup-sync",
                "instance": args.instance,
                "root_page": str(root_page.get("id", "")),
                "root_title": str(root_page.get("title", "")),
                "apply": args.apply and not args.dry_run,
                "skills": results,
                "index_updated": args.apply and not args.dry_run,
            },
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "reports" / "live_web_news"

DEFAULT_TIMEOUT = 8
MAX_PER_SOURCE = 4


@dataclass
class Source:
    section: str
    name: str
    url: str


SOURCES = [
    Source("A_EV_HYBRID", "Electrek", "https://electrek.co/feed/"),
    Source("A_EV_HYBRID", "InsideEVs", "https://insideevs.com/rss/news/"),
    Source("B_ROBOTICS", "The Robot Report", "https://www.therobotreport.com/feed/"),
    Source("B_ROBOTICS", "IEEE Spectrum Robotics", "https://spectrum.ieee.org/rss/robotics/fulltext"),
    Source("C_AI", "OpenAI News", "https://openai.com/news/rss.xml"),
    Source("C_AI", "arXiv cs.AI", "https://export.arxiv.org/rss/cs.AI"),
]


def _fetch_text(url: str, timeout: int) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; live-web-news/1.0)"})
    ssl_ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _find_text(elem: ET.Element, *tags: str) -> str:
    for tag in tags:
        node = elem.find(tag)
        if node is not None and node.text:
            return node.text.strip()
    return ""


def _parse_rss_or_atom(xml_text: str, limit: int) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    root = ET.fromstring(xml_text)

    # RSS 2.0
    channel = root.find("channel")
    if channel is not None:
        for item in channel.findall("item")[:limit]:
            title = _find_text(item, "title")
            link = _find_text(item, "link")
            published = _find_text(item, "pubDate")
            if title and link:
                items.append({"title": title, "link": link, "published": published})
        return items

    # Atom
    ns = "{http://www.w3.org/2005/Atom}"
    for entry in root.findall(f"{ns}entry")[:limit]:
        title = _find_text(entry, f"{ns}title")
        published = _find_text(entry, f"{ns}updated", f"{ns}published")
        link = ""
        link_node = entry.find(f"{ns}link")
        if link_node is not None:
            link = (link_node.attrib.get("href") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "published": published})
    return items


def collect_live_news(timeout: int, per_source: int) -> dict[str, Any]:
    now = dt.datetime.now()
    payload: dict[str, Any] = {
        "run_date": now.date().isoformat(),
        "generated_at": now.isoformat(timespec="seconds"),
        "sections": {
            "A_EV_HYBRID": [],
            "B_ROBOTICS": [],
            "C_AI": [],
        },
        "failures": [],
    }

    for src in SOURCES:
        try:
            xml_text = _fetch_text(src.url, timeout=timeout)
            parsed = _parse_rss_or_atom(xml_text, limit=per_source)
            for row in parsed:
                payload["sections"][src.section].append(
                    {
                        "source": src.name,
                        "title": row.get("title", ""),
                        "link": row.get("link", ""),
                        "published": row.get("published", ""),
                    }
                )
        except Exception as exc:  # pragma: no cover
            payload["failures"].append(f"{src.name}: {exc}")

    return payload


def _render_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Live Web News Brief")
    lines.append("")
    lines.append(f"- Run date: {payload['run_date']}")
    lines.append(f"- Generated at: {payload['generated_at']}")
    lines.append("- Source mode: direct web RSS/Atom (no local data-table dependency)")
    lines.append("")

    title_map = {
        "A_EV_HYBRID": "A. EV / Hybrid",
        "B_ROBOTICS": "B. Robotics / Embodied AI",
        "C_AI": "C. AI Research / Market",
    }

    for key in ["A_EV_HYBRID", "B_ROBOTICS", "C_AI"]:
        lines.append(f"## {title_map[key]}")
        lines.append("")
        rows = payload["sections"].get(key, [])
        if not rows:
            lines.append("- No live items collected from configured web sources.")
        else:
            for row in rows:
                source = row.get("source", "")
                title = row.get("title", "")
                link = row.get("link", "")
                published = row.get("published", "")
                lines.append(f"- [{title}]({link}) ({source})" + (f" | {published}" if published else ""))
        lines.append("")

    lines.append("## Source Health")
    lines.append("")
    if payload.get("failures"):
        for failure in payload["failures"]:
            lines.append(f"- {failure}")
    else:
        lines.append("- All sources fetched successfully.")
    lines.append("")
    return "\n".join(lines)


def _render_html(payload: dict[str, Any]) -> str:
    title_map = {
        "A_EV_HYBRID": "A. EV / Hybrid",
        "B_ROBOTICS": "B. Robotics / Embodied AI",
        "C_AI": "C. AI Research / Market",
    }

    css = """
    :root {
      --bg: #f6f2ea;
      --card: #fffdf7;
      --ink: #1c2430;
      --muted: #596477;
      --line: #d7c8b0;
      --accent: #0e7a6d;
      --accent-2: #b84d2a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      background: radial-gradient(circle at 20% 0%, #f3e9d8 0%, var(--bg) 50%) fixed;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.5;
    }
    .wrap {
      max-width: 1080px;
      margin: 24px auto;
      padding: 0 16px 24px;
    }
    .hero {
      background: linear-gradient(135deg, #fff8ea, #efe4cf);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px 20px;
      margin-bottom: 16px;
    }
    .meta { color: var(--muted); font-size: 14px; }
    .grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      min-height: 280px;
    }
    h1 { margin: 0 0 6px; font-size: 30px; }
    h2 { margin: 0 0 10px; font-size: 18px; color: var(--accent); }
    ul { margin: 0; padding-left: 18px; }
    li { margin: 0 0 8px; }
    a { color: var(--accent-2); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .source { color: var(--muted); font-size: 12px; }
    .health {
      margin-top: 14px;
      background: #fff8f4;
      border: 1px dashed #caa799;
      border-radius: 12px;
      padding: 12px;
    }
    @media (max-width: 900px) {
      .grid { grid-template-columns: 1fr; }
    }
    """

    parts: list[str] = []
    parts.append("<!doctype html>")
    parts.append("<html lang=\"en\"><head><meta charset=\"utf-8\" />")
    parts.append("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />")
    parts.append("<title>Live Web News Brief</title>")
    parts.append(f"<style>{css}</style></head><body>")
    parts.append("<div class=\"wrap\">")
    parts.append("<section class=\"hero\">")
    parts.append("<h1>Live Web News Brief</h1>")
    parts.append(
        f"<div class=\"meta\">Run date: {html.escape(payload['run_date'])} | Generated at: {html.escape(payload['generated_at'])}</div>"
    )
    parts.append("<div class=\"meta\">Direct web RSS/Atom collection; no local data-table dependency.</div>")
    parts.append("</section>")
    parts.append("<section class=\"grid\">")

    for key in ["A_EV_HYBRID", "B_ROBOTICS", "C_AI"]:
        rows = payload["sections"].get(key, [])
        parts.append("<article class=\"card\">")
        parts.append(f"<h2>{html.escape(title_map[key])}</h2>")
        if not rows:
            parts.append("<p>No live items collected from configured web sources.</p>")
        else:
            parts.append("<ul>")
            for row in rows:
                title = html.escape(row.get("title", ""))
                link = html.escape(row.get("link", ""))
                source = html.escape(row.get("source", ""))
                published = html.escape(row.get("published", ""))
                meta = f"{source}" + (f" | {published}" if published else "")
                parts.append(f"<li><a href=\"{link}\" target=\"_blank\" rel=\"noopener\">{title}</a><div class=\"source\">{meta}</div></li>")
            parts.append("</ul>")
        parts.append("</article>")

    parts.append("</section>")
    parts.append("<section class=\"health\"><strong>Source Health</strong><ul>")
    failures = payload.get("failures") or []
    if failures:
        for failure in failures:
            parts.append(f"<li>{html.escape(str(failure))}</li>")
    else:
        parts.append("<li>All sources fetched successfully.</li>")
    parts.append("</ul></section>")
    parts.append("</div></body></html>")
    return "".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build live news output from web feeds without local data tables.")
    parser.add_argument("--date", default="", help="Report date in YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP timeout seconds per source.")
    parser.add_argument("--max-per-source", type=int, default=MAX_PER_SOURCE, help="Max items per source.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = collect_live_news(timeout=args.timeout, per_source=args.max_per_source)

    report_date = args.date or payload["run_date"]
    output_dir = OUT_ROOT / report_date
    output_dir.mkdir(parents=True, exist_ok=True)

    md_text = _render_markdown(payload)
    html_text = _render_html(payload)

    (output_dir / f"live_web_news_{report_date}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / f"live_web_news_{report_date}.md").write_text(md_text + "\n", encoding="utf-8")
    (output_dir / f"live_web_news_{report_date}.html").write_text(html_text + "\n", encoding="utf-8")

    print(f"Run date: {report_date}")
    print(f"EV items: {len(payload['sections']['A_EV_HYBRID'])}")
    print(f"Robotics items: {len(payload['sections']['B_ROBOTICS'])}")
    print(f"AI items: {len(payload['sections']['C_AI'])}")
    print(f"Failures: {len(payload['failures'])}")
    print(f"Output: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

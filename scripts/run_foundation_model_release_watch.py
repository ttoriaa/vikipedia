#!/usr/bin/env python3
"""Periodic foundation-model release watch report generator.

The script collects provider updates from public RSS feeds, filters by a time
window, and emits a Markdown weekly brief plus a machine-readable JSON file.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


MODEL_HINT_PATTERNS = [
    r"gpt[- ]?\d(?:\.\d+)?",
    r"claude(?:[- ]?\d(?:\.\d+)?)?",
    r"gemini(?:[- ]?[\w.]+)?",
    r"deepseek[- ]?[\w.]+",
    r"kimi(?:[- ]?[\w.]+)?",
    r"glm[- ]?[\w.]+",
    r"qwen[- ]?[\w.]+",
    r"llama[- ]?[\w.]+",
    r"mistral[- ]?[\w.]+",
]


def _google_news_rss(query: str) -> str:
    return (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    )


PROVIDER_SOURCES: dict[str, list[str]] = {
    "openai": [
        "https://openai.com/news/rss.xml",
        _google_news_rss("OpenAI model release OR API pricing"),
    ],
    "anthropic": [
        _google_news_rss("Anthropic Claude release OR API pricing"),
    ],
    "google": [
        "https://blog.google/technology/ai/rss/",
        _google_news_rss("Google Gemini release OR Vertex AI model"),
    ],
    "deepseek": [
        _google_news_rss("DeepSeek model release OR API pricing"),
    ],
    "moonshot": [
        _google_news_rss("Moonshot Kimi model release OR API pricing"),
    ],
    "glm": [
        _google_news_rss("Zhipu GLM model release OR API pricing"),
    ],
    "qwen": [
        _google_news_rss("Qwen model release OR Alibaba Qwen API"),
    ],
    "meta": [
        _google_news_rss("Meta Llama model release OR API"),
    ],
    "mistral": [
        _google_news_rss("Mistral model release OR API pricing"),
    ],
}


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_text(element: ET.Element | None) -> str:
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def _parse_pub_date(raw: str) -> datetime | None:
    if not raw:
        return None

    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue

    return None


@dataclass
class FeedItem:
    provider: str
    title: str
    link: str
    published_at: datetime
    source_url: str
    snippet: str


def _fetch_xml(url: str, timeout: int) -> bytes:
    req = Request(url, headers={"User-Agent": "foundation-model-release-watch/1.0"})
    with urlopen(req, timeout=timeout) as response:
        return response.read()


def _extract_items(xml_bytes: bytes, provider: str, source_url: str) -> list[FeedItem]:
    items: list[FeedItem] = []

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return items

    rss_items = root.findall(".//item")
    for item in rss_items:
        title = _safe_text(item.find("title"))
        link = _safe_text(item.find("link"))
        snippet = _safe_text(item.find("description"))
        raw_date = _safe_text(item.find("pubDate"))
        published_at = _parse_pub_date(raw_date)
        if not title or not link or not published_at:
            continue
        items.append(
            FeedItem(
                provider=provider,
                title=title,
                link=link,
                published_at=published_at,
                source_url=source_url,
                snippet=snippet,
            )
        )

    atom_entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
    for entry in atom_entries:
        title = _safe_text(entry.find("{http://www.w3.org/2005/Atom}title"))
        link_node = entry.find("{http://www.w3.org/2005/Atom}link")
        link = ""
        if link_node is not None:
            link = (link_node.attrib.get("href") or "").strip()
        snippet = _safe_text(entry.find("{http://www.w3.org/2005/Atom}summary"))
        if not snippet:
            snippet = _safe_text(entry.find("{http://www.w3.org/2005/Atom}content"))
        raw_date = _safe_text(entry.find("{http://www.w3.org/2005/Atom}updated"))
        if not raw_date:
            raw_date = _safe_text(entry.find("{http://www.w3.org/2005/Atom}published"))
        published_at = _parse_pub_date(raw_date)
        if not title or not link or not published_at:
            continue
        items.append(
            FeedItem(
                provider=provider,
                title=title,
                link=link,
                published_at=published_at,
                source_url=source_url,
                snippet=snippet,
            )
        )

    return items


def _detect_model_hints(text: str) -> list[str]:
    hits: list[str] = []
    for pattern in MODEL_HINT_PATTERNS:
        for matched in re.findall(pattern, text, flags=re.IGNORECASE):
            norm = re.sub(r"\s+", " ", matched.strip())
            if norm and norm.lower() not in {h.lower() for h in hits}:
                hits.append(norm)
    return hits


def _default_providers() -> list[str]:
    return [
        "openai",
        "anthropic",
        "google",
        "deepseek",
        "moonshot",
        "glm",
        "qwen",
    ]


def _parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    dt = datetime.strptime(value, "%Y-%m-%d")
    return dt.replace(tzinfo=timezone.utc)


def _render_markdown(
    report_date: datetime,
    cadence: str,
    window_days: int,
    providers: list[str],
    grouped_items: dict[str, list[dict[str, Any]]],
    failures: list[dict[str, str]],
    language: str,
) -> str:
    period_start = (report_date - timedelta(days=window_days)).date().isoformat()
    period_end = report_date.date().isoformat()

    lines: list[str] = []
    lines.append("# Foundation Model Release Watch")
    lines.append("")
    lines.append("## A. Executive Summary")
    lines.append("")
    lines.append(f"- Date: {period_end}")
    lines.append(f"- Cadence: {cadence}")
    lines.append(f"- Window: {period_start} to {period_end} ({window_days} days)")
    lines.append(f"- Providers covered: {', '.join(providers)}")

    total_updates = sum(len(grouped_items.get(p, [])) for p in providers)
    lines.append(f"- Total tracked updates: {total_updates}")
    if failures:
        lines.append(f"- Source fetch warnings: {len(failures)}")
    lines.append("")

    lines.append("## B. Provider-by-Provider Updates")
    lines.append("")
    for provider in providers:
        updates = grouped_items.get(provider, [])
        lines.append(f"### {provider}")
        if not updates:
            lines.append("- No update in the selected window.")
            lines.append("")
            continue

        for idx, item in enumerate(updates, start=1):
            date_str = item["published_at"]
            hints = item.get("model_hints", [])
            hint_text = ", ".join(hints) if hints else "n/a"
            lines.append(f"{idx}. {item['title']}")
            lines.append(f"   - Date: {date_str}")
            lines.append(f"   - Model hints: {hint_text}")
            lines.append(f"   - Source: {item['link']}")
        lines.append("")

    lines.append("## C. Cross-Vendor Comparison Table")
    lines.append("")
    lines.append("| Provider | Updates | Notable Model Hints |")
    lines.append("|---|---:|---|")
    for provider in providers:
        updates = grouped_items.get(provider, [])
        hints: list[str] = []
        for item in updates:
            for hint in item.get("model_hints", []):
                if hint.lower() not in {x.lower() for x in hints}:
                    hints.append(hint)
        hints_text = ", ".join(hints[:5]) if hints else "n/a"
        lines.append(f"| {provider} | {len(updates)} | {hints_text} |")
    lines.append("")

    lines.append("## D. Enterprise Adoption Signals and Risks")
    lines.append("")
    lines.append("- Signal: Monitor pricing or API packaging updates as direct cost drivers.")
    lines.append("- Signal: Track model hint frequency to identify active release cycles.")
    lines.append("- Risk: Some providers may rely on secondary coverage if official feeds are limited.")
    lines.append("- Risk: Unverified claims should remain pending until an official source is available.")
    lines.append("")

    lines.append("## E. Next Watchlist")
    lines.append("")
    lines.append("- Check official release-note pages for each provider at least once per week.")
    lines.append("- Track API pricing page changes and enterprise policy updates.")
    lines.append("- Maintain the same provider universe for trend comparability.")
    lines.append("")

    if failures:
        lines.append("## Source Fetch Warnings")
        lines.append("")
        for failure in failures:
            lines.append(f"- {failure['provider']}: {failure['source']} -> {failure['error']}")
        lines.append("")

    if language in {"zh", "bilingual"}:
        lines.append("## 中文补充")
        lines.append("")
        lines.append("- 本周报告聚焦各厂商模型发布、价格变化和企业可落地信号。")
        lines.append("- 建议将新增发布与上一期基线进行差异标注，用于管理层复盘。")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a periodic foundation model release watch report.")
    parser.add_argument("--date", default=None, help="Report date in YYYY-MM-DD format. Default is today (UTC).")
    parser.add_argument("--cadence", default="weekly", choices=["daily", "weekly"], help="Report cadence.")
    parser.add_argument("--window-days", type=int, default=7, help="Lookback window in days.")
    parser.add_argument(
        "--providers",
        default=",".join(_default_providers()),
        help="Comma-separated providers. Example: openai,anthropic,google,deepseek,moonshot,glm,qwen",
    )
    parser.add_argument("--max-items", type=int, default=5, help="Maximum updates per provider.")
    parser.add_argument("--language", default="bilingual", choices=["zh", "en", "bilingual"], help="Output language mode.")
    parser.add_argument("--dry-run", default="true", help="true/false. Dry run means no external publish actions.")
    parser.add_argument("--emit-json", default=None, help="Optional JSON output path.")
    parser.add_argument("--request-timeout", type=int, default=15, help="HTTP timeout in seconds.")
    args = parser.parse_args()

    report_date = _parse_date(args.date)
    since = report_date - timedelta(days=args.window_days)
    dry_run = _parse_bool(args.dry_run)

    providers = [p.strip().lower() for p in args.providers.split(",") if p.strip()]
    providers = [p for p in providers if p in PROVIDER_SOURCES]
    if not providers:
        print("No valid providers selected.", file=sys.stderr)
        return 2

    failures: list[dict[str, str]] = []
    grouped: dict[str, list[FeedItem]] = {provider: [] for provider in providers}

    for provider in providers:
        for source in PROVIDER_SOURCES.get(provider, []):
            try:
                payload = _fetch_xml(source, timeout=args.request_timeout)
                grouped[provider].extend(_extract_items(payload, provider=provider, source_url=source))
            except URLError as err:
                failures.append({"provider": provider, "source": source, "error": str(err)})
            except Exception as err:  # noqa: BLE001
                failures.append({"provider": provider, "source": source, "error": str(err)})

    normalized_grouped: dict[str, list[dict[str, Any]]] = {}
    for provider in providers:
        seen: set[str] = set()
        updates: list[dict[str, Any]] = []

        ordered = sorted(grouped.get(provider, []), key=lambda x: x.published_at, reverse=True)
        for item in ordered:
            if item.published_at < since:
                continue
            key = (item.link or item.title).strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            model_hints = _detect_model_hints(f"{item.title} {item.snippet}")
            updates.append(
                {
                    "provider": provider,
                    "title": item.title,
                    "link": item.link,
                    "published_at": item.published_at.date().isoformat(),
                    "source_url": item.source_url,
                    "model_hints": model_hints,
                }
            )
            if len(updates) >= args.max_items:
                break

        normalized_grouped[provider] = updates

    markdown = _render_markdown(
        report_date=report_date,
        cadence=args.cadence,
        window_days=args.window_days,
        providers=providers,
        grouped_items=normalized_grouped,
        failures=failures,
        language=args.language,
    )

    root = Path(__file__).resolve().parents[1]
    report_dir = root / "reports" / "foundation_model_release_watch" / report_date.date().isoformat()
    report_dir.mkdir(parents=True, exist_ok=True)

    md_path = report_dir / "foundation_model_release_watch.md"
    md_path.write_text(markdown, encoding="utf-8")

    summary = {
        "date": report_date.date().isoformat(),
        "cadence": args.cadence,
        "window_days": args.window_days,
        "providers": providers,
        "dry_run": dry_run,
        "items": normalized_grouped,
        "failures": failures,
        "markdown_path": str(md_path),
    }

    json_path = Path(args.emit_json) if args.emit_json else (report_dir / "foundation_model_release_watch.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    latest_md = root / "reports" / "foundation_model_release_watch" / "latest.md"
    latest_md.write_text(markdown, encoding="utf-8")

    print("Foundation model release watch completed.")
    print(f"- Date: {summary['date']}")
    print(f"- Providers: {', '.join(providers)}")
    print(f"- Markdown: {md_path}")
    print(f"- JSON: {json_path}")
    print(f"- Failures: {len(failures)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run daily multi-market news research and render Markdown/JSON outputs."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

ROOT = Path.cwd()
SCRIPT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = SCRIPT_ROOT / "config" / "default_sources.json"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "daily_market_news"


@dataclass
class NewsItem:
    title: str
    link: str
    source: str
    published: str
    market: str
    markets: set[str] = field(default_factory=set)
    symbols: set[str] = field(default_factory=set)
    themes: set[str] = field(default_factory=set)
    query_terms: set[str] = field(default_factory=set)

    def key(self) -> str:
        base = self.link or self.title
        normalized = re.sub(r"\s+", " ", base.strip().lower())
        return hashlib.sha1(normalized.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "link": self.link,
            "source": self.source,
            "published": self.published,
            "market": self.market,
            "markets": sorted(self.markets),
            "symbols": sorted(self.symbols),
            "themes": sorted(self.themes),
            "query_terms": sorted(self.query_terms),
        }


def str_to_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in re.split(r"[\s,]+", value) if part.strip()]


def split_comma_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def normalize_market_codes(raw_markets: list[str], config: dict[str, Any]) -> list[str]:
    available = config.get("markets", {})
    markets = [market.strip().lower() for market in raw_markets if market.strip()]
    if not markets:
        markets = list(available.keys())
    invalid = [market for market in markets if market not in available]
    if invalid:
        raise ValueError(f"Unknown market code(s): {', '.join(invalid)}")
    return markets


def build_query_terms(mode: str, config: dict[str, Any], markets: list[str], symbols: list[str], themes: list[str]) -> list[dict[str, Any]]:
    market_cfg = config.get("markets", {})
    symbol_aliases = config.get("symbol_aliases", {})
    theme_aliases = config.get("themes", {})

    queries: list[dict[str, Any]] = []
    if mode in {"watchlist", "mixed"}:
        watch_symbols = symbols[:]
        if not watch_symbols:
            for market in markets:
                watch_symbols.extend(market_cfg.get(market, {}).get("default_symbols", []))
        for market in markets:
            for symbol in watch_symbols:
                aliases = symbol_aliases.get(symbol, [symbol])
                queries.append(
                    {
                        "kind": "symbol",
                        "market": market,
                        "symbol": symbol,
                        "query_terms": list(dict.fromkeys([symbol, *aliases])),
                    }
                )

    if mode in {"theme", "mixed"}:
        topic_names = themes[:] or list(theme_aliases.keys())
        for market in markets:
            for theme in topic_names:
                aliases = theme_aliases.get(theme, [theme])
                queries.append(
                    {
                        "kind": "theme",
                        "market": market,
                        "theme": theme,
                        "query_terms": list(dict.fromkeys([theme, *aliases])),
                    }
                )

    if not queries:
        raise ValueError("No queries configured. Provide symbols and/or themes, or use mixed mode.")
    return queries


def make_search_url(config: dict[str, Any], market: str, query_terms: list[str], limit: int) -> str:
    market_cfg = config["markets"][market]
    template = config["source_templates"]["google_news_rss"]
    query_text = " OR ".join(f'"{term}"' if " " in term else term for term in query_terms)
    query_text = f"({query_text}) when:1d"
    return template.format(
        query=quote_plus(query_text),
        hl=market_cfg["hl"],
        gl=market_cfg["gl"],
        ceid=market_cfg["ceid"],
        limit=limit,
    )


def make_bing_search_url(config: dict[str, Any], query_terms: list[str]) -> str:
    template = config["source_templates"]["bing_news_rss"]
    query_text = " OR ".join(f'"{term}"' if " " in term else term for term in query_terms)
    return template.format(query=quote_plus(query_text))


def make_exchange_search_url(config: dict[str, Any], market: str, query_terms: list[str], limit: int) -> str:
    market_cfg = config["markets"][market]
    template = config["source_templates"]["exchange_google_rss"]
    exchange_cfg = (config.get("exchange_sources") or {}).get(market, {})
    filters = [f"site:{site}" for site in exchange_cfg.get("site_filters", [])]
    base_query = " OR ".join(f'"{term}"' if " " in term else term for term in query_terms)
    filter_query = " OR ".join(filters)
    if filter_query:
        query_text = f"({base_query}) ({filter_query}) when:7d"
    else:
        query_text = f"({base_query}) when:7d"
    return template.format(
        query=quote_plus(query_text),
        hl=market_cfg["hl"],
        gl=market_cfg["gl"],
        ceid=market_cfg["ceid"],
        limit=limit,
    )


def make_yahoo_rss_url(config: dict[str, Any], symbol: str) -> str:
    template = config["source_templates"]["yahoo_finance_rss"]
    return template.format(symbol=quote_plus(symbol))


def make_arxiv_url(config: dict[str, Any], query_terms: list[str], limit: int) -> str:
    template = config["source_templates"]["arxiv_api"]
    query_text = " OR ".join(f'"{term}"' if " " in term else term for term in query_terms)
    return template.format(query=quote_plus(query_text), limit=limit)


def fetch_text(url: str, timeout: int = 20) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml,application/xml,text/xml,text/plain,*/*",
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def parse_feed(xml_text: str, market: str) -> list[NewsItem]:
    root = ET.fromstring(xml_text)
    items: list[NewsItem] = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        source = (item.findtext("./source") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if not title and not link:
            continue
        items.append(
            NewsItem(
                title=title or link,
                link=link,
                source=source or extract_source_from_title(title),
                published=pub_date,
                market=market,
            )
        )
    return items


def parse_sec_atom_feed(xml_text: str, market: str) -> list[NewsItem]:
    root = ET.fromstring(xml_text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items: list[NewsItem] = []
    for entry in root.findall("atom:entry", ns):
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        updated = (entry.findtext("atom:updated", default="", namespaces=ns) or "").strip()
        link = ""
        for link_node in entry.findall("atom:link", ns):
            href = (link_node.attrib.get("href") or "").strip()
            if href:
                link = href
                break
        if not title and not link:
            continue
        items.append(
            NewsItem(
                title=title or link,
                link=link,
                source="SEC",
                published=updated,
                market=market,
            )
        )
    return items


def parse_atom_feed(xml_text: str, market: str, source_name: str) -> list[NewsItem]:
    root = ET.fromstring(xml_text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items: list[NewsItem] = []
    for entry in root.findall("atom:entry", ns):
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        updated = (entry.findtext("atom:updated", default="", namespaces=ns) or "").strip()
        link = ""
        for link_node in entry.findall("atom:link", ns):
            href = (link_node.attrib.get("href") or "").strip()
            rel = (link_node.attrib.get("rel") or "").strip()
            if href and (not rel or rel == "alternate"):
                link = href
                break
        if not title and not link:
            continue
        items.append(
            NewsItem(
                title=title or link,
                link=link,
                source=source_name,
                published=updated,
                market=market,
            )
        )
    return items


def extract_source_from_title(title: str) -> str:
    if " - " in title:
        return title.rsplit(" - ", 1)[-1].strip()
    return "Google News"


def fetch_items_for_query(
    config: dict[str, Any],
    query: dict[str, Any],
    max_items: int,
    request_timeout: int,
) -> tuple[list[NewsItem], list[str]]:
    items: list[NewsItem] = []
    errors: list[str] = []
    market = query["market"]
    enabled_sources = (config.get("source_policy") or {}).get(
        "enabled", ["google_news_rss", "bing_news_rss", "yahoo_finance_rss", "arxiv_api", "exchange_announcements"]
    )

    if "google_news_rss" in enabled_sources:
        url = make_search_url(config, market, query["query_terms"], max_items)
        try:
            xml_text = fetch_text(url, timeout=request_timeout)
            items.extend(parse_feed(xml_text, market)[:max_items])
        except (HTTPError, URLError, ET.ParseError, TimeoutError, ValueError) as exc:
            errors.append(f"google_news_rss:{exc}")

    if "bing_news_rss" in enabled_sources:
        url = make_bing_search_url(config, query["query_terms"])
        try:
            xml_text = fetch_text(url, timeout=request_timeout)
            items.extend(parse_feed(xml_text, market)[:max_items])
        except (HTTPError, URLError, ET.ParseError, TimeoutError, ValueError) as exc:
            errors.append(f"bing_news_rss:{exc}")

    if "yahoo_finance_rss" in enabled_sources and query.get("kind") == "symbol":
        symbol = str(query.get("symbol") or "").strip()
        if symbol:
            url = make_yahoo_rss_url(config, symbol)
            try:
                xml_text = fetch_text(url, timeout=request_timeout)
                parsed = parse_feed(xml_text, market)
                for item in parsed:
                    if not item.source:
                        item.source = "Yahoo Finance"
                items.extend(parsed[:max_items])
            except (HTTPError, URLError, ET.ParseError, TimeoutError, ValueError) as exc:
                errors.append(f"yahoo_finance_rss:{exc}")

    if "arxiv_api" in enabled_sources and query.get("kind") == "theme":
        theme = str(query.get("theme") or "").strip().lower()
        if theme in {"ai papers", "ai paradigm", "llm releases"}:
            url = make_arxiv_url(config, query["query_terms"], max_items)
            try:
                xml_text = fetch_text(url, timeout=request_timeout)
                items.extend(parse_atom_feed(xml_text, market, "arXiv")[:max_items])
            except (HTTPError, URLError, ET.ParseError, TimeoutError, ValueError) as exc:
                errors.append(f"arxiv_api:{exc}")

    if "exchange_announcements" in enabled_sources:
        exchange_cfg = (config.get("exchange_sources") or {}).get(market, {})

        sec_atom_url = (exchange_cfg.get("sec_atom") or "").strip() if market == "us" else ""
        if sec_atom_url:
            try:
                atom_text = fetch_text(sec_atom_url, timeout=request_timeout)
                items.extend(parse_sec_atom_feed(atom_text, market)[:max_items])
            except (HTTPError, URLError, ET.ParseError, TimeoutError, ValueError) as exc:
                errors.append(f"exchange_announcements_sec_atom:{exc}")

        exchange_url = make_exchange_search_url(config, market, query["query_terms"], max_items)
        try:
            xml_text = fetch_text(exchange_url, timeout=request_timeout)
            items.extend(parse_feed(xml_text, market)[:max_items])
        except (HTTPError, URLError, ET.ParseError, TimeoutError, ValueError) as exc:
            errors.append(f"exchange_announcements_google:{exc}")

    return items, errors


def merge_item(target: NewsItem, incoming: NewsItem, query_terms: list[str]) -> None:
    target.markets.add(incoming.market)
    target.symbols.update(incoming.symbols)
    target.themes.update(incoming.themes)
    target.query_terms.update(query_terms)
    if not target.source and incoming.source:
        target.source = incoming.source
    if not target.published and incoming.published:
        target.published = incoming.published


def classify_item(item: NewsItem, symbols: list[str], themes: list[str], symbol_aliases: dict[str, list[str]], theme_aliases: dict[str, list[str]]) -> None:
    lower = f"{item.title} {item.source}".lower()
    for symbol in symbols:
        aliases = symbol_aliases.get(symbol, [symbol])
        if any(alias.lower() in lower for alias in aliases):
            item.symbols.add(symbol)
    for theme in themes:
        aliases = theme_aliases.get(theme, [theme])
        if any(alias.lower() in lower for alias in aliases):
            item.themes.add(theme)


def dedupe_items(
    raw_items: list[tuple[NewsItem, dict[str, Any]]],
    symbols: list[str],
    themes: list[str],
    symbol_aliases: dict[str, list[str]],
    theme_aliases: dict[str, list[str]],
) -> list[NewsItem]:
    by_key: dict[str, NewsItem] = {}
    for item, query in raw_items:
        classify_item(item, symbols, themes, symbol_aliases, theme_aliases)
        item.markets.add(query["market"])
        if query.get("symbol"):
            item.symbols.add(query["symbol"])
        if query.get("theme"):
            item.themes.add(query["theme"])
        item.query_terms.update(query.get("query_terms", []))
        key = item.key()
        if key not in by_key:
            by_key[key] = item
            continue
        merge_item(by_key[key], item, query.get("query_terms", []))
    return sorted(by_key.values(), key=lambda x: (x.published, x.title), reverse=True)


def group_items(items: list[NewsItem], key: str) -> dict[str, list[NewsItem]]:
    grouped: dict[str, list[NewsItem]] = {}
    for item in items:
        labels = sorted(getattr(item, key))
        if not labels:
            labels = ["unclassified"]
        for label in labels:
            grouped.setdefault(label, []).append(item)
    return grouped


def localized_labels(language: str, market_cfg: dict[str, Any]) -> tuple[str, str]:
    zh = market_cfg.get("label_zh", "")
    en = market_cfg.get("label_en", "")
    if language == "zh":
        return zh, ""
    if language == "en":
        return en, ""
    return zh, en


def render_markdown(
    report_date: str,
    mode: str,
    markets: list[str],
    language: str,
    config: dict[str, Any],
    items: list[NewsItem],
    failures: list[str],
    output_path: Path,
    max_items: int,
) -> None:
    lines: list[str] = []
    title = "Daily Market News Research / 每日多市场新闻简报" if language == "bilingual" else "Daily Market News Research"
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- Date / 日期: {report_date}")
    lines.append(f"- Mode / 模式: {mode}")
    lines.append(f"- Markets / 市场: {', '.join(markets)}")
    lines.append(f"- Items / 条目: {len(items)}")
    if failures:
        lines.append(f"- Source warnings / 来源警告: {len(failures)}")
    lines.append("")

    market_cfg = config.get("markets", {})
    grouped_by_market = group_items(items, "markets")
    for market in markets:
        label_zh, label_en = localized_labels(language, market_cfg.get(market, {}))
        heading = f"## {label_zh}" if language == "zh" else f"## {label_en}" if language == "en" else f"## {label_zh} / {label_en}"
        lines.append(heading)
        market_items = grouped_by_market.get(market, [])[:max_items]
        if not market_items:
            lines.append("- No items found / 暂无结果")
            lines.append("")
            continue
        for item in market_items:
            tags = []
            if item.symbols:
                tags.append(f"symbols={','.join(sorted(item.symbols))}")
            if item.themes:
                tags.append(f"themes={','.join(sorted(item.themes))}")
            tag_text = f" ({'; '.join(tags)})" if tags else ""
            lines.append(f"- [{item.title}]({item.link}){tag_text}")
            if item.source:
                lines.append(f"  - Source / 来源: {item.source}")
            if item.published:
                lines.append(f"  - Published / 时间: {item.published}")
        lines.append("")

    grouped_by_theme = group_items(items, "themes")
    if grouped_by_theme:
        lines.append("## Themes / 主题")
        for theme, theme_items in sorted(grouped_by_theme.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            lines.append(f"### {theme}")
            for item in theme_items[:max_items]:
                lines.append(f"- [{item.title}]({item.link}) | {item.source or 'Google News'}")
            lines.append("")

    lines.append("## Notes / 说明")
    lines.append("- Public-web-first source policy is used by default.")
    lines.append("- The script deduplicates by canonical link/title and keeps source links for traceability.")
    if failures:
        lines.append("- Failed sources were skipped, not retried aggressively.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def render_json_payload(
    report_date: str,
    mode: str,
    markets: list[str],
    language: str,
    items: list[NewsItem],
    failures: list[str],
) -> dict[str, Any]:
    return {
        "date": report_date,
        "mode": mode,
        "markets": markets,
        "language": language,
        "item_count": len(items),
        "failures": failures,
        "items": [item.to_dict() for item in items],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run daily multi-market news research")
    parser.add_argument("--date", default=dt.datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--mode", choices=["watchlist", "theme", "mixed"], default="mixed")
    parser.add_argument("--markets", default="us,cn,kr,hk")
    parser.add_argument("--symbols", default="")
    parser.add_argument("--themes", default="")
    parser.add_argument("--max-items", type=int, default=10)
    parser.add_argument("--language", choices=["zh", "en", "bilingual"], default="bilingual")
    parser.add_argument("--request-timeout", type=int, default=15)
    parser.add_argument("--dry-run", default="true")
    parser.add_argument("--emit-json", default="")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    markets = normalize_market_codes(split_csv(args.markets), config)
    symbols = split_comma_list(args.symbols)
    themes = split_comma_list(args.themes)
    query_specs = build_query_terms(args.mode, config, markets, symbols, themes)

    raw_items: list[tuple[NewsItem, dict[str, Any]]] = []
    failures: list[str] = []
    for query in query_specs:
        items, errors = fetch_items_for_query(config, query, args.max_items, args.request_timeout)
        for err in errors:
            failures.append(f"{query['market']}:{query.get('symbol') or query.get('theme')}: {err}")
        for item in items[:args.max_items]:
            raw_items.append((item, query))

    symbol_aliases = config.get("symbol_aliases", {})
    theme_aliases = config.get("themes", {})
    items = dedupe_items(raw_items, symbols, themes, symbol_aliases, theme_aliases)

    out_dir = Path(args.output_dir) / args.date
    markdown_path = out_dir / f"daily_market_news_{args.date}.md"
    json_path = out_dir / f"daily_market_news_{args.date}.json"
    render_markdown(args.date, args.mode, markets, args.language, config, items, failures, markdown_path, args.max_items)

    if args.emit_json:
        emit_path = Path(args.emit_json)
        if not emit_path.is_absolute():
            emit_path = ROOT / emit_path
        emit_path.parent.mkdir(parents=True, exist_ok=True)
        emit_path.write_text(json.dumps(render_json_payload(args.date, args.mode, markets, args.language, items, failures), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(render_json_payload(args.date, args.mode, markets, args.language, items, failures), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    dry_run = str_to_bool(args.dry_run)
    print(json.dumps({
        "date": args.date,
        "mode": args.mode,
        "markets": markets,
        "item_count": len(items),
        "failures": failures,
        "markdown_path": str(markdown_path),
        "json_path": str(args.emit_json or json_path),
        "dry_run": dry_run,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
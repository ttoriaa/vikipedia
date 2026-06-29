#!/usr/bin/env python3
"""Update market_watch data with configurable alerts, multi-source news digest, and Feishu delivery."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import random
import statistics
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "market_watch" / "data"
HISTORY_ROOT = OUT_ROOT / "history"
ALERTS_ROOT = OUT_ROOT / "alerts"
ALERTS_HISTORY_ROOT = ALERTS_ROOT / "history"
DIGEST_ROOT = OUT_ROOT / "digest"
DIGEST_HISTORY_ROOT = DIGEST_ROOT / "history"
SNAPSHOT_INDEX = OUT_ROOT / "snapshots_index.json"
LATEST_QUOTES = OUT_ROOT / "quotes_latest.json"
LATEST_ALERTS = ALERTS_ROOT / "latest_alerts.json"
LATEST_DIGEST = DIGEST_ROOT / "latest_digest.json"
ALERT_RULES_PATH = ROOT / "market_watch" / "alert_rules.json"
NOTIFY_STATE_PATH = OUT_ROOT / "notify_state.json"

CATEGORY_SYMBOLS = {
    "semiconductor": ["SOXX", "NVDA", "TSM", "ASML"],
    "ai_compute": ["NVDA", "AMD", "SMCI", "QQQ"],
    "robotics": ["TSLA", "ABB", "SYM", "PATH"],
    "llm_releases": ["MSFT", "GOOG", "META", "AMZN"],
    "ai_apps": ["DUOL", "ADBE", "CRM", "PLTR"],
    "energy": ["CL=F", "BZ=F", "XLE", "ICLN"],
    "gold": ["GC=F", "XAUUSD=X", "GLD"],
}

CATEGORY_DISPLAY = {
    "semiconductor": "半导体",
    "ai_compute": "AI算力",
    "robotics": "机器人/具身智能",
    "llm_releases": "LLM发布",
    "ai_apps": "AI应用",
    "energy": "能源",
    "gold": "黄金",
}

CATEGORY_NEWS_KEYWORDS = {
    "semiconductor": ["semiconductor", "chip", "NVIDIA", "TSMC", "ASML", "半导体"],
    "ai_compute": ["AI compute", "GPU", "NVIDIA", "AMD", "SMCI", "算力"],
    "robotics": ["robotics", "humanoid", "Tesla Optimus", "UBTECH", "Figure AI", "机器人", "具身智能"],
    "llm_releases": ["LLM", "GPT", "Claude", "Gemini", "foundation model", "模型发布", "版本更新"],
    "ai_apps": ["AI app", "copilot", "agent", "enterprise AI", "AI应用", "AI产品"],
    "energy": ["oil", "WTI", "Brent", "XLE", "新能源", "能源"],
    "gold": ["gold", "XAU", "COMEX", "GLD", "黄金"],
}

DEFAULT_RULES = {
    "intraday": {
        "daily_move_abs_pct": 2.0,
        "breakout_window_days": 20,
        "volume_spike_multiple": 1.8,
        "min_history_for_volume": 5,
    },
    "post_close": {
        "daily_move_abs_pct": 1.5,
        "breakout_window_days": 20,
        "volume_spike_multiple": 1.5,
        "min_history_for_volume": 5,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update market_watch data")
    parser.add_argument("--snapshot-date", default="", help="Snapshot date YYYY-MM-DD (defaults to current UTC date)")
    parser.add_argument(
        "--snapshot-type",
        choices=["intraday", "post_close"],
        default="intraday",
        help="Snapshot type marker",
    )
    parser.add_argument("--keep-days", type=int, default=180, help="How many recent days to keep in history")
    parser.add_argument("--dry-run", action="store_true", help="Compute outputs but do not write files")
    parser.add_argument("--notify-feishu", action="store_true", help="Send alerts to Feishu webhook")
    parser.add_argument("--notify-dry-run", action="store_true", help="Print Feishu payload instead of sending")
    parser.add_argument("--skip-news", action="store_true", help="Skip all news fetching")
    parser.add_argument("--request-timeout", type=int, default=12, help="HTTP timeout in seconds")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_json(path: Path, payload: dict[str, Any], dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fetch_text(url: str, timeout: int = 25) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*,application/rss+xml,application/xml",
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def fetch_json(url: str, timeout: int = 25) -> dict[str, Any]:
    return json.loads(fetch_text(url, timeout=timeout))


def safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def source_status(name: str, ok: bool, error: str = "") -> dict[str, Any]:
    return {"source": name, "ok": ok, "error": error}


def load_alert_rules() -> dict[str, Any]:
    payload = load_json(ALERT_RULES_PATH)
    if not payload:
        return dict(DEFAULT_RULES)
    return {
        "intraday": {**DEFAULT_RULES["intraday"], **(payload.get("intraday") or {})},
        "post_close": {**DEFAULT_RULES["post_close"], **(payload.get("post_close") or {})},
    }


def fetch_yahoo_quotes(symbols: list[str], request_timeout: int = 12) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if not symbols:
        return {}, [source_status("yahoo", True)]

    url = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=" + quote_plus(",".join(symbols))
    try:
        payload = fetch_json(url, timeout=request_timeout)
        results = payload.get("quoteResponse", {}).get("result", [])
        out: dict[str, dict[str, Any]] = {}
        for item in results:
            symbol = str(item.get("symbol", "")).strip()
            if not symbol:
                continue
            out[symbol] = {
                "price": safe_float(item.get("regularMarketPrice")),
                "prev_close": safe_float(item.get("regularMarketPreviousClose")),
                "change_pct": safe_float(item.get("regularMarketChangePercent")),
                "volume": safe_float(item.get("regularMarketVolume")),
                "timestamp": int(item.get("regularMarketTime") or 0),
                "currency": str(item.get("currency") or ""),
                "source": "yahoo",
            }
        return out, [source_status("yahoo", True)]
    except (HTTPError, URLError, json.JSONDecodeError) as exc:
        return {}, [source_status("yahoo", False, str(exc))]


def fetch_alpha_vantage_quote(symbol: str, request_timeout: int = 12) -> dict[str, Any] | None:
    key = os.getenv("ALPHAVANTAGE_API_KEY", "").strip()
    if not key:
        return None

    url = (
        "https://www.alphavantage.co/query?function=GLOBAL_QUOTE"
        f"&symbol={quote_plus(symbol)}&apikey={quote_plus(key)}"
    )
    try:
        payload = fetch_json(url, timeout=request_timeout)
        quote = payload.get("Global Quote", {})
        if not quote:
            return None
        price = safe_float(quote.get("05. price"))
        prev_close = safe_float(quote.get("08. previous close"))
        change_pct = safe_float(str(quote.get("10. change percent") or "").replace("%", ""))
        volume = safe_float(quote.get("06. volume"))
        if price is None:
            return None
        return {
            "price": price,
            "prev_close": prev_close,
            "change_pct": change_pct,
            "volume": volume,
            "timestamp": 0,
            "currency": "USD",
            "source": "alpha_vantage",
        }
    except (HTTPError, URLError, json.JSONDecodeError):
        return None


def fetch_cn_quote(symbol: str, request_timeout: int = 12) -> dict[str, Any] | None:
    mapping = {
        "GC=F": "hf_GC",
        "CL=F": "hf_CL",
        "BZ=F": "hf_OIL",
    }
    code = mapping.get(symbol)
    if not code:
        return None

    url = f"https://hq.sinajs.cn/list={code}"
    try:
        text = fetch_text(url, timeout=request_timeout)
        if "=" not in text:
            return None
        body = text.split("=", 1)[1].strip().strip(";\"")
        parts = body.split(",")
        if len(parts) < 2:
            return None
        price = safe_float(parts[0])
        prev_close = safe_float(parts[1])
        if price is None:
            return None
        change_pct = None
        if prev_close and prev_close != 0:
            change_pct = (price - prev_close) / prev_close * 100
        return {
            "price": price,
            "prev_close": prev_close,
            "change_pct": change_pct,
            "volume": None,
            "timestamp": 0,
            "currency": "USD",
            "source": "cn_feed",
        }
    except Exception:
        return None


def merge_quotes(category_map: dict[str, list[str]], request_timeout: int = 12) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    universe: list[str] = []
    for symbols in category_map.values():
        universe.extend(symbols)
    symbols = sorted(set(universe))

    yahoo_data, statuses = fetch_yahoo_quotes(symbols, request_timeout=request_timeout)

    rows: list[dict[str, Any]] = []
    used_alpha = False
    used_cn = False

    for category, category_symbols in category_map.items():
        for symbol in category_symbols:
            row = dict(yahoo_data.get(symbol, {}))
            if not row.get("price"):
                fallback = fetch_alpha_vantage_quote(symbol, request_timeout=request_timeout)
                if fallback:
                    row = fallback
                    used_alpha = True
            if not row.get("price"):
                cn_fallback = fetch_cn_quote(symbol, request_timeout=request_timeout)
                if cn_fallback:
                    row = cn_fallback
                    used_cn = True

            rows.append(
                {
                    "category": category,
                    "category_display": CATEGORY_DISPLAY.get(category, category),
                    "symbol": symbol,
                    "price": row.get("price"),
                    "prev_close": row.get("prev_close"),
                    "change_pct": row.get("change_pct"),
                    "volume": row.get("volume"),
                    "timestamp": row.get("timestamp"),
                    "currency": row.get("currency") or "",
                    "source": row.get("source") or "missing",
                }
            )

    if used_alpha:
        statuses.append(source_status("alpha_vantage", True))
    elif os.getenv("ALPHAVANTAGE_API_KEY", "").strip():
        statuses.append(source_status("alpha_vantage", False, "unused_or_rate_limited"))
    else:
        statuses.append(source_status("alpha_vantage", False, "missing_api_key"))

    statuses.append(source_status("cn_feeds", used_cn, "fallback_only" if used_cn else "not_hit"))
    return rows, statuses


def load_snapshot_quotes(date_str: str) -> list[dict[str, Any]]:
    path = HISTORY_ROOT / date_str / "quotes.json"
    payload = load_json(path)
    if not payload:
        return []
    data = payload.get("quotes")
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def build_symbol_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "").strip()
        if symbol:
            out[symbol] = row
    return out


def recent_dates(index_payload: dict[str, Any], limit: int = 20) -> list[str]:
    snapshots = index_payload.get("snapshots", []) if isinstance(index_payload, dict) else []
    dates = [item.get("date") for item in snapshots if isinstance(item, dict) and item.get("date")]
    return sorted(set(dates), reverse=True)[:limit]


def compute_alerts(
    today_quotes: list[dict[str, Any]],
    index_payload: dict[str, Any],
    snapshot_type: str,
    rules: dict[str, Any],
) -> list[dict[str, Any]]:
    cfg = rules.get(snapshot_type, DEFAULT_RULES[snapshot_type])
    move_threshold = safe_float(cfg.get("daily_move_abs_pct")) or DEFAULT_RULES[snapshot_type]["daily_move_abs_pct"]
    breakout_window = int(cfg.get("breakout_window_days") or DEFAULT_RULES[snapshot_type]["breakout_window_days"])
    volume_multiple = safe_float(cfg.get("volume_spike_multiple")) or DEFAULT_RULES[snapshot_type]["volume_spike_multiple"]
    min_history_for_volume = int(cfg.get("min_history_for_volume") or DEFAULT_RULES[snapshot_type]["min_history_for_volume"])

    alerts: list[dict[str, Any]] = []
    today_map = build_symbol_map(today_quotes)
    dates = recent_dates(index_payload, max(30, breakout_window + 5))
    history_maps = [build_symbol_map(load_snapshot_quotes(d)) for d in dates]

    for symbol, row in today_map.items():
        price = safe_float(row.get("price"))
        change_pct = safe_float(row.get("change_pct"))
        volume = safe_float(row.get("volume"))
        category = row.get("category")

        if change_pct is not None and abs(change_pct) >= move_threshold:
            alerts.append(
                {
                    "symbol": symbol,
                    "category": category,
                    "rule": "daily_move",
                    "snapshot_type": snapshot_type,
                    "severity": "high" if abs(change_pct) >= move_threshold * 1.8 else "medium",
                    "message": f"{symbol} {snapshot_type} 涨跌幅 {change_pct:.2f}% (阈值 {move_threshold:.2f}%)",
                    "value": change_pct,
                }
            )

        history_prices: list[float] = []
        history_volumes: list[float] = []
        for mp in history_maps[:breakout_window]:
            item = mp.get(symbol)
            if not item:
                continue
            p = safe_float(item.get("price"))
            v = safe_float(item.get("volume"))
            if p is not None:
                history_prices.append(p)
            if v is not None:
                history_volumes.append(v)

        if price is not None and history_prices:
            max_window = max(history_prices)
            min_window = min(history_prices)
            if price > max_window:
                alerts.append(
                    {
                        "symbol": symbol,
                        "category": category,
                        "rule": "breakout_window_high",
                        "snapshot_type": snapshot_type,
                        "severity": "high",
                        "message": f"{symbol} 突破近{breakout_window}日新高",
                        "value": price,
                    }
                )
            elif price < min_window:
                alerts.append(
                    {
                        "symbol": symbol,
                        "category": category,
                        "rule": "breakout_window_low",
                        "snapshot_type": snapshot_type,
                        "severity": "high",
                        "message": f"{symbol} 跌破近{breakout_window}日新低",
                        "value": price,
                    }
                )

        if volume is not None and len(history_volumes) >= min_history_for_volume:
            avg_vol = statistics.fmean(history_volumes)
            if avg_vol > 0 and volume >= avg_vol * volume_multiple:
                alerts.append(
                    {
                        "symbol": symbol,
                        "category": category,
                        "rule": "volume_spike",
                        "snapshot_type": snapshot_type,
                        "severity": "medium",
                        "message": f"{symbol} 成交量放大至 {volume / avg_vol:.2f}x (阈值 {volume_multiple:.2f}x)",
                        "value": volume,
                    }
                )

    dedup: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in alerts:
        key = (str(item.get("symbol")), str(item.get("rule")), str(item.get("snapshot_type")))
        existing = dedup.get(key)
        if not existing:
            dedup[key] = item
            continue
        if str(item.get("severity")) == "high" and str(existing.get("severity")) != "high":
            dedup[key] = item
    return sorted(dedup.values(), key=lambda x: (x.get("severity") != "high", str(x.get("symbol"))))


def parse_rss_headlines(rss_text: str, limit: int = 4) -> list[str]:
    out: list[str] = []
    try:
        root = ET.fromstring(rss_text)
    except ET.ParseError:
        return out

    for item in root.findall(".//item"):
        title_node = item.find("title")
        if title_node is None or not title_node.text:
            continue
        title = html.unescape(title_node.text).strip()
        if not title or title.lower() == "google news":
            continue
        if title in out:
            continue
        out.append(title)
        if len(out) >= limit:
            break
    return out


def fetch_google_news_headlines(keyword: str, limit: int = 4, request_timeout: int = 12) -> list[str]:
    rss_url = (
        "https://news.google.com/rss/search?hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        f"&q={quote_plus(keyword)}"
    )
    try:
        text = fetch_text(rss_url, timeout=request_timeout)
    except Exception:
        return []
    return parse_rss_headlines(text, limit=limit)


def fetch_yahoo_news_headlines(symbol: str, limit: int = 4, request_timeout: int = 12) -> list[str]:
    rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={quote_plus(symbol)}&region=US&lang=en-US"
    try:
        text = fetch_text(rss_url, timeout=request_timeout)
    except Exception:
        return []
    return parse_rss_headlines(text, limit=limit)


def fetch_cn_news_headlines(keyword: str, limit: int = 4, request_timeout: int = 12) -> list[str]:
    rss_url = f"https://rsshub.app/sina/finance/stock/{quote_plus(keyword)}"
    try:
        text = fetch_text(rss_url, timeout=request_timeout)
    except Exception:
        return []
    return parse_rss_headlines(text, limit=limit)


def rank_digest_summary(rows: list[dict[str, Any]]) -> str:
    valid = [r for r in rows if safe_float(r.get("change_pct")) is not None]
    if not valid:
        return "暂无可用行情，建议关注后续更新。"

    sorted_rows = sorted(valid, key=lambda x: abs(safe_float(x.get("change_pct")) or 0), reverse=True)
    top = sorted_rows[:3]
    movers = ", ".join(f"{r.get('symbol')} {safe_float(r.get('change_pct')):.2f}%" for r in top)

    ups = [safe_float(r.get("change_pct")) for r in valid if (safe_float(r.get("change_pct")) or 0) > 0]
    downs = [safe_float(r.get("change_pct")) for r in valid if (safe_float(r.get("change_pct")) or 0) < 0]
    avg = statistics.fmean([safe_float(r.get("change_pct")) or 0 for r in valid])

    tone = "偏强" if avg > 0 else "偏弱"
    return f"板块{tone}，平均涨跌幅 {avg:.2f}% 。主要波动: {movers}。上涨 {len(ups)} 只，下跌 {len(downs)} 只。"


def unique_headlines(items: list[str], limit: int = 6) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for h in items:
        cleaned = h.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
        if len(out) >= limit:
            break
    return out


def build_digest(today_quotes: list[dict[str, Any]], skip_news: bool = False, request_timeout: int = 12) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for category, symbols in CATEGORY_SYMBOLS.items():
        rows = [r for r in today_quotes if r.get("category") == category]
        summary = rank_digest_summary(rows)

        headlines_google: list[str] = []
        headlines_yahoo: list[str] = []
        headlines_cn: list[str] = []
        if not skip_news:
            keyword = " ".join(CATEGORY_NEWS_KEYWORDS.get(category, symbols[:2]))
            headlines_google = fetch_google_news_headlines(keyword, request_timeout=request_timeout)
            headlines_yahoo = fetch_yahoo_news_headlines(symbols[0], request_timeout=request_timeout)
            headlines_cn = fetch_cn_news_headlines(CATEGORY_DISPLAY.get(category, category), request_timeout=request_timeout)

        merged_headlines = unique_headlines(headlines_google + headlines_yahoo + headlines_cn, limit=8)
        sections.append(
            {
                "category": category,
                "category_display": CATEGORY_DISPLAY.get(category, category),
                "summary": summary,
                "headlines": merged_headlines,
                "headline_by_source": {
                    "google_news_rss": headlines_google,
                    "yahoo_finance_rss": headlines_yahoo,
                    "cn_rsshub_proxy": headlines_cn,
                },
                "sources": ["google_news_rss", "yahoo_finance_rss", "cn_rsshub_proxy"],
                "quality": {
                    "headlines_count": len(merged_headlines),
                    "has_summary": True,
                },
            }
        )
    return sections


def upsert_snapshot_index(index_path: Path, date_str: str, snapshot_type: str, keep_days: int, dry_run: bool) -> dict[str, Any]:
    current = load_json(index_path) or {"generated_at": "", "snapshots": []}
    snapshots = current.get("snapshots", [])
    if not isinstance(snapshots, list):
        snapshots = []

    file_rel = f"market_watch/data/history/{date_str}/quotes.json"
    found = False
    for item in snapshots:
        if not isinstance(item, dict):
            continue
        if item.get("date") == date_str:
            item["file"] = file_rel
            item["snapshot_type"] = snapshot_type
            found = True
            break

    if not found:
        snapshots.append({"date": date_str, "file": file_rel, "snapshot_type": snapshot_type})

    snapshots = [s for s in snapshots if isinstance(s, dict) and s.get("date") and s.get("file")]
    snapshots.sort(key=lambda x: str(x.get("date")), reverse=True)
    if keep_days > 0:
        snapshots = snapshots[:keep_days]

    out = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "snapshots": snapshots,
    }
    write_json(index_path, out, dry_run=dry_run)
    return out


def build_feishu_payload(date_str: str, snapshot_type: str, alerts: list[dict[str, Any]], digest: list[dict[str, Any]]) -> dict[str, Any]:
    top_alerts = [a for a in alerts if a.get("severity") == "high"][:8]
    lines = [f"【Market Watch】{date_str} {snapshot_type}"]

    if top_alerts:
        lines.append("高优先级告警:")
        for item in top_alerts:
            lines.append(f"- {item.get('message')}")
    else:
        lines.append("高优先级告警: 无")

    lines.append("摘要:")
    for section in digest:
        lines.append(f"- {section.get('category_display')}: {section.get('summary')}")

    return {
        "msg_type": "text",
        "content": {"text": "\n".join(lines)},
    }


def compute_notify_idempotency_key(date_str: str, snapshot_type: str, alerts: list[dict[str, Any]], digest: list[dict[str, Any]]) -> str:
    seed = {
        "date": date_str,
        "snapshot_type": snapshot_type,
        "alerts": [
            {
                "symbol": a.get("symbol"),
                "rule": a.get("rule"),
                "severity": a.get("severity"),
                "value": a.get("value"),
            }
            for a in alerts
        ],
        "digest": [
            {
                "category": d.get("category"),
                "summary": d.get("summary"),
                "headlines": d.get("headlines"),
            }
            for d in digest
        ],
    }
    raw = json.dumps(seed, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def load_notify_state() -> dict[str, Any]:
    return load_json(NOTIFY_STATE_PATH) or {"last_idempotency_key": "", "sent_at": ""}


def save_notify_state(state: dict[str, Any], dry_run: bool) -> None:
    write_json(NOTIFY_STATE_PATH, state, dry_run=dry_run)


def send_feishu(payload: dict[str, Any], notify_dry_run: bool, request_timeout: int = 12, max_retries: int = 3) -> tuple[bool, str]:
    if notify_dry_run:
        print("[notify-dry-run] feishu payload:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return True, "dry-run"

    webhook = os.getenv("FEISHU_MARKET_WEBHOOK", "").strip()
    if not webhook:
        return False, "missing FEISHU_MARKET_WEBHOOK"

    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = Request(webhook, data=raw, headers={"Content-Type": "application/json"}, method="POST")
    last_error = ""
    for attempt in range(1, max_retries + 1):
        try:
            body = urlopen(req, timeout=request_timeout).read().decode("utf-8", errors="ignore")
            return True, body
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            if attempt < max_retries:
                time.sleep((2 ** (attempt - 1)) + random.random())
    return False, last_error


def main() -> int:
    args = parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    snapshot_date = args.snapshot_date.strip() or now.date().isoformat()

    quotes, source_states = merge_quotes(CATEGORY_SYMBOLS, request_timeout=args.request_timeout)
    index_payload = upsert_snapshot_index(
        SNAPSHOT_INDEX,
        snapshot_date,
        args.snapshot_type,
        args.keep_days,
        args.dry_run,
    )

    rules = load_alert_rules()
    alerts = compute_alerts(quotes, index_payload, snapshot_type=args.snapshot_type, rules=rules)
    digest_sections = build_digest(quotes, skip_news=args.skip_news, request_timeout=args.request_timeout)

    quotes_payload = {
        "meta": {
            "generated_at": now.isoformat(),
            "snapshot_date": snapshot_date,
            "snapshot_type": args.snapshot_type,
            "sources": [s.get("source") for s in source_states],
            "source_status": source_states,
            "status": "ok" if any(s.get("ok") for s in source_states) else "degraded",
        },
        "quotes": quotes,
    }

    alerts_payload = {
        "meta": {
            "generated_at": now.isoformat(),
            "snapshot_date": snapshot_date,
            "snapshot_type": args.snapshot_type,
            "rules": rules.get(args.snapshot_type, DEFAULT_RULES[args.snapshot_type]),
        },
        "alerts": alerts,
    }

    digest_payload = {
        "meta": {
            "generated_at": now.isoformat(),
            "snapshot_date": snapshot_date,
            "snapshot_type": args.snapshot_type,
            "news_sources": ["google_news_rss", "yahoo_finance_rss", "cn_rsshub_proxy"],
        },
        "sections": digest_sections,
    }

    daily_quotes = HISTORY_ROOT / snapshot_date / "quotes.json"
    daily_alerts = ALERTS_HISTORY_ROOT / snapshot_date / "alerts.json"
    daily_digest = DIGEST_HISTORY_ROOT / snapshot_date / "digest.json"

    write_json(LATEST_QUOTES, quotes_payload, args.dry_run)
    write_json(daily_quotes, quotes_payload, args.dry_run)
    write_json(LATEST_ALERTS, alerts_payload, args.dry_run)
    write_json(daily_alerts, alerts_payload, args.dry_run)
    write_json(LATEST_DIGEST, digest_payload, args.dry_run)
    write_json(daily_digest, digest_payload, args.dry_run)

    notify_result = "skip"
    idempotency_key = compute_notify_idempotency_key(snapshot_date, args.snapshot_type, alerts, digest_sections)
    if args.notify_feishu or args.notify_dry_run:
        state = load_notify_state()
        last_key = str(state.get("last_idempotency_key") or "")
        if not args.notify_dry_run and last_key == idempotency_key:
            notify_result = "skip_duplicate"
        else:
            payload = build_feishu_payload(snapshot_date, args.snapshot_type, alerts, digest_sections)
            ok, info = send_feishu(
                payload,
                notify_dry_run=args.notify_dry_run,
                request_timeout=args.request_timeout,
                max_retries=3,
            )
            notify_result = "ok" if ok else f"failed: {info}"
            if ok and not args.notify_dry_run:
                save_notify_state(
                    {
                        "last_idempotency_key": idempotency_key,
                        "sent_at": now.isoformat(),
                        "snapshot_date": snapshot_date,
                        "snapshot_type": args.snapshot_type,
                    },
                    dry_run=args.dry_run,
                )

    report = {
        "snapshot_date": snapshot_date,
        "snapshot_type": args.snapshot_type,
        "quotes_count": len(quotes),
        "alerts_count": len(alerts),
        "digest_sections": len(digest_sections),
        "notify": notify_result,
        "idempotency_key": idempotency_key,
        "dry_run": args.dry_run,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

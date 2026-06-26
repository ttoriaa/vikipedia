#!/usr/bin/env python3
"""Refresh AI hardware industry chain JSON feed with lightweight market signals."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

YAHOO_QUOTE_ENDPOINT = "https://query1.finance.yahoo.com/v7/finance/quote"
USER_AGENT = "vikipedia-ai-hardware-sync/1.0"

DEFAULT_LAYERS: list[dict[str, Any]] = [
    {
        "layer": "GPU / AI Accelerator",
        "companies": ["NVIDIA", "AMD", "Intel", "Huawei Ascend", "Cambricon"],
        "bom": "45%-60%",
        "shortage": "High",
        "tickers": ["NVDA", "AMD", "INTC", "688256.SS"],
    },
    {
        "layer": "HBM",
        "companies": ["SK hynix", "Samsung", "Micron"],
        "bom": "12%-22%",
        "shortage": "High",
        "tickers": ["000660.KS", "005930.KS", "MU"],
    },
    {
        "layer": "Advanced Packaging",
        "companies": ["TSMC", "Samsung", "Intel", "ASE", "Amkor", "JCET"],
        "bom": "5%-10%",
        "shortage": "High",
        "tickers": ["TSM", "INTC", "ASX", "AMKR", "600584.SS"],
    },
    {
        "layer": "ABF Substrate",
        "companies": ["Ibiden", "Shinko", "Unimicron", "Nan Ya PCB", "Kinsus", "AT&S"],
        "bom": "2%-4%",
        "shortage": "Medium",
        "tickers": ["4062.TW", "3189.TW", "8046.TW"],
    },
    {
        "layer": "AI PCB",
        "companies": ["Compeq", "Unitech PCB", "TTM", "Shennan", "WUS", "Gold Circuit"],
        "bom": "3%-6%",
        "shortage": "Medium",
        "tickers": ["2313.TW", "TTMI", "002916.SZ", "002463.SZ"],
    },
    {
        "layer": "High-speed Connectors",
        "companies": ["Amphenol", "TE", "Molex", "JAE", "Luxshare", "FIT"],
        "bom": "2%-5%",
        "shortage": "Medium",
        "tickers": ["APH", "TEL", "002475.SZ", "6088.HK"],
    },
    {
        "layer": "MLCC",
        "companies": ["Murata", "TDK", "Taiyo Yuden", "SEMCO", "Yageo", "Walsin"],
        "bom": "1%-3%",
        "shortage": "Low-Medium",
        "tickers": ["6981.T", "6762.T", "2379.TW", "2492.TW", "009150.KS"],
    },
]


def fetch_quotes(symbols: list[str], timeout: int) -> dict[str, dict[str, Any]]:
    if not symbols:
        return {}
    query = parse.urlencode({"symbols": ",".join(symbols)})
    url = f"{YAHOO_QUOTE_ENDPOINT}?{query}"
    req = request.Request(url)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", USER_AGENT)

    with request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    results: list[dict[str, Any]] = (((payload.get("quoteResponse") or {}).get("result")) or [])
    mapped: dict[str, dict[str, Any]] = {}
    for item in results:
        symbol = str(item.get("symbol") or "").strip()
        if not symbol:
            continue
        mapped[symbol] = {
            "symbol": symbol,
            "name": item.get("shortName") or item.get("longName") or symbol,
            "currency": item.get("currency") or "",
            "price": item.get("regularMarketPrice"),
            "change_pct": item.get("regularMarketChangePercent"),
            "market_time": item.get("regularMarketTime"),
        }
    return mapped


def build_action_template(shortage: str) -> dict[str, str]:
    if shortage == "High":
        return {
            "lock_volume": "2-4 quarters rolling lock",
            "dual_source": "Parallel primary and backup qualification where feasible",
            "buffer": "8-12 weeks",
            "delivery_plan": "Back-schedule rack delivery from memory and packaging availability",
        }
    if shortage == "Medium":
        return {
            "lock_volume": "1-2 quarters framework lock",
            "dual_source": "Dual source for new programs and backup validation for mass production",
            "buffer": "4-8 weeks",
            "delivery_plan": "Quarterly cadence review and lead-time correction",
        }
    return {
        "lock_volume": "Monthly replenishment with forecast guardrails",
        "dual_source": "Keep switchable approved vendor list",
        "buffer": "2-4 weeks",
        "delivery_plan": "Demand spike trigger threshold to avoid overstock",
    }


def enrich_layers(layers: list[dict[str, Any]], timeout: int) -> list[dict[str, Any]]:
    symbols: list[str] = []
    for layer in layers:
        symbols.extend(layer.get("tickers") or [])

    quotes: dict[str, dict[str, Any]] = {}
    fetch_error = ""
    try:
        quotes = fetch_quotes(symbols, timeout=timeout)
    except (error.HTTPError, error.URLError, TimeoutError, ValueError) as exc:
        fetch_error = str(exc)

    enriched: list[dict[str, Any]] = []
    for layer in layers:
        tickers = layer.get("tickers") or []
        quote_items = [quotes[t] for t in tickers if t in quotes]
        change_values = [q.get("change_pct") for q in quote_items if isinstance(q.get("change_pct"), (int, float))]
        avg_change = round(sum(change_values) / len(change_values), 3) if change_values else None

        enriched.append(
            {
                "layer": layer["layer"],
                "companies": layer["companies"],
                "bom": layer["bom"],
                "shortage": layer["shortage"],
                "tickers": tickers,
                "market_signal": {
                    "quote_count": len(quote_items),
                    "avg_change_pct": avg_change,
                    "quotes": quote_items,
                    "fetch_error": fetch_error,
                },
                "procurement_action_template": build_action_template(layer["shortage"]),
            }
        )
    return enriched


def build_payload(layers: list[dict[str, Any]], timeout: int) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "generated_at": now.isoformat(),
        "date": now.date().isoformat(),
        "perspective": "buyer",
        "horizon": "12-24m",
        "source": {
            "quote_api": YAHOO_QUOTE_ENDPOINT,
            "description": "Daily refreshed baseline + market quote signals",
        },
        "layers": enrich_layers(layers, timeout=timeout),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh AI hardware industry chain JSON feed")
    parser.add_argument("--output", default="assets/ai-hardware-industry-chain/latest.json")
    parser.add_argument("--history-dir", default="assets/ai-hardware-industry-chain/history")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--skip-history", action="store_true")
    args = parser.parse_args()

    payload = build_payload(DEFAULT_LAYERS, timeout=args.timeout)
    output_path = Path(args.output)
    write_json(output_path, payload)

    if not args.skip_history:
        date = payload.get("date") or datetime.now(timezone.utc).date().isoformat()
        history_path = Path(args.history_dir) / f"{date}.json"
        write_json(history_path, payload)

    print(f"WROTE={output_path}")
    if not args.skip_history:
        print(f"WROTE_HISTORY={Path(args.history_dir) / ((payload.get('date') or 'unknown') + '.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

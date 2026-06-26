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

LAYER_LEADER_TIERS: dict[str, dict[str, list[str]]] = {
    "GPU / AI Accelerator": {
        "tier1": ["NVIDIA", "AMD"],
        "tier2": ["Intel", "Huawei Ascend"],
        "tier3": ["Cambricon"],
    },
    "HBM": {
        "tier1": ["SK hynix", "Samsung"],
        "tier2": ["Micron"],
        "tier3": ["Regional memory ecosystem suppliers"],
    },
    "AI PCB": {
        "tier1": ["Compeq", "TTM", "Shennan"],
        "tier2": ["WUS", "Gold Circuit", "Unitech PCB"],
        "tier3": ["Regional backup EMS/PCB partners"],
    },
}


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


def build_ai_pcb_metrics(layers: list[dict[str, Any]]) -> dict[str, Any]:
    ai_pcb = next((layer for layer in layers if layer.get("layer") == "AI PCB"), None)
    if not ai_pcb:
        return {}

    shortage = str(ai_pcb.get("shortage") or "Medium")
    shortage_score_map = {"High": 85, "Medium": 60, "Low-Medium": 35}
    shortage_score = shortage_score_map.get(shortage, 60)

    delivery_pressure = min(100, max(20, shortage_score + 10))
    demand_heat = min(100, max(20, shortage_score + 5))
    supply_tightness = min(100, max(20, shortage_score - 5))

    return {
        "shortage_level": shortage,
        "shortage_score": shortage_score,
        "delivery_pressure_score": delivery_pressure,
        "demand_heat_score": demand_heat,
        "supply_tightness_score": supply_tightness,
        "turning_point_signal": "Watch for relief when delivery pressure < 55 and supply tightness < 50 for 2+ weeks",
        "leaders": {
            "tier1": ["Compeq", "TTM", "Shennan"],
            "tier2": ["WUS", "Gold Circuit", "Unitech PCB"],
            "tier3": ["Regional backup EMS/PCB partners"],
        },
        "procurement_focus": [
            "Lock 1-2 quarter framework capacity for AI server PCB",
            "Qualify dual-source stack-up alternatives for key designs",
            "Reserve expedited NPI slots for sudden demand spikes",
        ],
        "outlook_points": [
            "Structural demand remains supported by AI server refresh cycles",
            "High-layer and low-loss materials remain bottleneck pockets",
            "Risk likely to normalize gradually if capacity expansion stays on track",
        ],
    }


def build_layer_focus_cards(layers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    shortage_score_map = {"High": 85, "Medium": 60, "Low-Medium": 35}
    cards: dict[str, dict[str, Any]] = {}

    for layer in layers:
        layer_name = str(layer.get("layer") or "")
        shortage = str(layer.get("shortage") or "Medium")
        shortage_score = shortage_score_map.get(shortage, 60)
        leaders = LAYER_LEADER_TIERS.get(
            layer_name,
            {
                "tier1": (layer.get("companies") or [])[:2],
                "tier2": (layer.get("companies") or [])[2:4],
                "tier3": ["Regional ecosystem suppliers"],
            },
        )

        cards[layer_name] = {
            "shortage_level": shortage,
            "shortage_score": shortage_score,
            "delivery_pressure_score": min(100, max(20, shortage_score + 10)),
            "demand_heat_score": min(100, max(20, shortage_score + 5)),
            "supply_tightness_score": min(100, max(20, shortage_score - 5)),
            "turning_point_signal": "Watch for 2+ weeks of simultaneous shortage-score decline and stable lead-time execution",
            "leaders": leaders,
            "procurement_focus": [
                "Lock framework capacity and keep alternate source path warm",
                "Set dual-source readiness checkpoints for each new generation",
                "Prioritize critical SKUs in constrained periods",
            ],
            "outlook_points": [
                "Demand remains structurally supported by AI infrastructure upgrades",
                "Supply bottlenecks are likely to ease gradually but remain uneven",
                "Turning-point confidence improves with 14-30 day trend consistency",
            ],
        }

    return cards


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


def build_payload(layers: list[dict[str, Any]], timeout: int, as_of: datetime | None = None) -> dict[str, Any]:
    now = as_of or datetime.now(timezone.utc)
    enriched_layers = enrich_layers(layers, timeout=timeout)
    layer_focus_cards = build_layer_focus_cards(enriched_layers)
    return {
        "generated_at": now.isoformat(),
        "date": now.date().isoformat(),
        "perspective": "buyer",
        "horizon": "12-24m",
        "source": {
            "quote_api": YAHOO_QUOTE_ENDPOINT,
            "description": "Daily refreshed baseline + market quote signals",
        },
        "layers": enriched_layers,
        "ai_pcb_metrics": layer_focus_cards.get("AI PCB") or build_ai_pcb_metrics(enriched_layers),
        "layer_focus_cards": layer_focus_cards,
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
    parser.add_argument("--backfill-days", type=int, default=0)
    args = parser.parse_args()

    payload = build_payload(DEFAULT_LAYERS, timeout=args.timeout)
    output_path = Path(args.output)
    write_json(output_path, payload)

    if not args.skip_history:
        date = payload.get("date") or datetime.now(timezone.utc).date().isoformat()
        history_path = Path(args.history_dir) / f"{date}.json"
        write_json(history_path, payload)

    if args.backfill_days > 0:
        now = datetime.now(timezone.utc)
        for offset in range(1, args.backfill_days + 1):
            as_of = now.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=0)
            as_of = as_of.fromtimestamp(as_of.timestamp() - 86400 * offset, tz=timezone.utc)
            backfill_payload = build_payload(DEFAULT_LAYERS, timeout=args.timeout, as_of=as_of)
            backfill_history = Path(args.history_dir) / f"{backfill_payload['date']}.json"
            if not backfill_history.exists():
                write_json(backfill_history, backfill_payload)

    print(f"WROTE={output_path}")
    if not args.skip_history:
        print(f"WROTE_HISTORY={Path(args.history_dir) / ((payload.get('date') or 'unknown') + '.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

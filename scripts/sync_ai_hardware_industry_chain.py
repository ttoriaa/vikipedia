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

LAYER_FOCUS_PROFILES: dict[str, dict[str, list[str] | str]] = {
    "GPU / AI Accelerator": {
        "summary": "需求主轴仍在模型训练、推理扩容与服务器刷新，GPU 仍是整个链条的最强定价锚。",
        "drivers": ["超大规模训练集群持续扩容", "推理侧带来更广泛的出货基础", "新架构迭代同时抬升封装和 HBM 拉动"],
        "bottlenecks": ["HBM 供给节拍", "先进封装排产", "整机功耗与散热设计"],
        "weekly_report": {
            "this_week": ["云厂商 capex 维持高位，主流平台出货节奏仍偏强"],
            "next_week": ["继续观察新平台 SKU 放量和整机交付 lead time 是否稳定"],
            "risk_flags": ["若 HBM 或封装排产再度吃紧，GPU 端交付会被动拉长"],
        },
        "cycle_position": "structural_upcycle",
    },
    "HBM": {
        "summary": "HBM 仍是 AI 服务器最关键的紧缺件之一，容量扩张与良率爬坡决定供需改善速度。",
        "drivers": ["训练/推理都在提高单卡带宽要求", "高堆叠容量已成为平台升级前提", "HBM3E/HBM4 认证推进带来替换窗口"],
        "bottlenecks": ["封装与测试产能", "高堆叠良率", "先进节点材料与基板协同"],
        "weekly_report": {
            "this_week": ["头部厂扩产继续推进，但有效供给释放仍受良率约束"],
            "next_week": ["关注客户认证结果和季度出货结构是否向更高堆叠产品迁移"],
            "risk_flags": ["若认证延后或良率改善慢于预期，紧缺度会维持高位"],
        },
        "cycle_position": "tight_capacity",
    },
    "Advanced Packaging": {
        "summary": "先进封装是 GPU/HBM 放量的同步约束，产能与工艺窗口决定整条链的兑现速度。",
        "drivers": ["Chiplet 和高算力平台渗透率上升", "2.5D/3D 方案提高单位封装价值量", "大客户拉货对产线优先级的虹吸效应"],
        "bottlenecks": ["CoWoS/类似产线排程", "ABF/载板/中介层协同", "测试与良率爬坡"],
        "weekly_report": {
            "this_week": ["大客户需求仍在虹吸产线，扩产节奏继续是市场关注点"],
            "next_week": ["观察封装厂扩产计划和中介层/基板备料是否同步到位"],
            "risk_flags": ["若测试良率或排产受阻，整条 AI 服务器链交付会继续被拖慢"],
        },
        "cycle_position": "capacity_constrained",
    },
    "ABF Substrate": {
        "summary": "ABF 基板处于高端载板供给的咽喉位置，AI 芯片叠层复杂度持续抬升单位面积需求。",
        "drivers": ["高 I/O 高层数封装需求上升", "服务器平台升级推高材料规格", "低损耗/高层数产品占比提升"],
        "bottlenecks": ["高层数良率", "玻纤/树脂/铜箔材料协同", "扩产爬坡周期长"],
        "weekly_report": {
            "this_week": ["高层数和低损耗料号仍是主线，头部厂排产优先级较高"],
            "next_week": ["跟踪主力厂扩线公告和客户试产节奏，判断供给改善拐点"],
            "risk_flags": ["若玻纤/树脂/铜箔协同不足，ABF 仍会在局部规格上卡脖子"],
        },
        "cycle_position": "selectively_tight",
    },
    "AI PCB": {
        "summary": "AI PCB 是服务器整机交付的关键承接层，低损耗、高层数与高速信号完整性共同决定供给弹性。",
        "drivers": ["AI 服务器平台刷新带动高层板需求", "更高功耗/更高速率提升材料要求", "板级设计复杂度继续上升"],
        "bottlenecks": ["高层数板制程", "低损耗材料供应", "认证周期与良率爬坡"],
        "weekly_report": {
            "this_week": ["高层板与 HDI 交付周期仍是核心变量，客户对双供的偏好更明确"],
            "next_week": ["重点看主力厂接单节奏和认证推进，判断产能是否开始松动"],
            "risk_flags": ["若低损耗材料供应或良率爬坡跟不上，交付压力会快速回升"],
        },
        "cycle_position": "design_complexity_up",
    },
    "High-speed Connectors": {
        "summary": "高速连接器的价值在于信号完整性和装配可靠性，平台升级会放大头部供应商的认证壁垒。",
        "drivers": ["GPU/交换机/机柜链路速率提升", "更高功耗推动高可靠连接方案", "模块化平台加大接口数量"],
        "bottlenecks": ["材料与接触电阻控制", "高速认证周期", "结构件和装配公差"],
        "weekly_report": {
            "this_week": ["接口速率升级带动新品导入，头部厂仍占据认证优势"],
            "next_week": ["观察平台接口规格变化和 OEM 新料号导入节奏"],
            "risk_flags": ["若材料或接触电阻控制不稳，高速链路良率会先受影响"],
        },
        "cycle_position": "spec_upgrade",
    },
    "MLCC": {
        "summary": "MLCC 在 AI 服务器链中更偏稳定消耗件，但高容高压与高频料号仍会出现局部紧张。",
        "drivers": ["电源管理与去耦需求提升", "服务器功耗上行带来更高规格料号占比", "车规/工控与 AI 共享产能"],
        "bottlenecks": ["高端小型化料号产能", "关键客户配额", "高频高容规格切换"],
        "weekly_report": {
            "this_week": ["整体偏稳定，但高规格料号仍能看到局部拉货"],
            "next_week": ["继续跟踪头部厂稼动率、高端料号交期和客户库存回补节奏"],
            "risk_flags": ["若客户集中补库，高频高容料号会先出现周期性紧张"],
        },
        "cycle_position": "mostly_stable",
    },
}


def build_layer_profile(layer_name: str, shortage: str, layer: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = LAYER_FOCUS_PROFILES.get(layer_name, {})
    shortage_score_map = {"High": 85, "Medium": 60, "Low-Medium": 35}
    shortage_score = shortage_score_map.get(shortage, 60)
    market_signal = (layer or {}).get("market_signal") or {}
    avg_change_pct = market_signal.get("avg_change_pct") if isinstance(market_signal, dict) else None
    quote_count = market_signal.get("quote_count") if isinstance(market_signal, dict) else None

    return {
        "summary": profile.get("summary") or f"{layer_name} 仍受 AI 服务器链条驱动，供需改善速度取决于上游产能释放与客户认证节奏。",
        "drivers": profile.get("drivers") or ["AI 服务器需求延续", "平台升级带来的规格提升", "客户认证推动头部集中度上升"],
        "bottlenecks": profile.get("bottlenecks") or ["供给端扩产节拍", "高规格材料/工艺门槛", "量产良率与认证周期"],
        "weekly_report": profile.get("weekly_report") or {
            "this_week": ["产能扩张和交期变化仍是本周最重要的监测点"],
            "next_week": ["继续跟踪双供导入和客户认证推进情况"],
            "risk_flags": ["若供给释放慢于需求，局部规格仍会维持紧张"],
        },
        "cycle_position": profile.get("cycle_position") or "balanced",
        "market_signal_avg_change_pct": avg_change_pct,
        "market_signal_quote_count": quote_count,
        "shortage_level": shortage,
        "shortage_score": shortage_score,
        "delivery_pressure_score": min(100, max(20, shortage_score + 10)),
        "demand_heat_score": min(100, max(20, shortage_score + 5)),
        "supply_tightness_score": min(100, max(20, shortage_score - 5)),
        "turning_point_signal": "Watch for 2+ weeks of simultaneous shortage-score decline and stable lead-time execution",
        "leaders": LAYER_LEADER_TIERS.get(
            layer_name,
            {
                "tier1": [],
                "tier2": [],
                "tier3": ["Regional ecosystem suppliers"],
            },
        ),
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
    cards: dict[str, dict[str, Any]] = {}

    for layer in layers:
        layer_name = str(layer.get("layer") or "")
        shortage = str(layer.get("shortage") or "Medium")
        cards[layer_name] = build_layer_profile(layer_name, shortage, layer)

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

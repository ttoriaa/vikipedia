#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHARGING_ROOT = ROOT / "reports" / "dongchedi_daily"
MOTOR_ROOT = ROOT / "reports" / "dongchedi_motor_daily"
NEWS_ROOT = ROOT / "reports" / "daily_market_news"
MARKET_WATCH_ROOT = ROOT / "market_watch" / "data"
OUT_ROOT = ROOT / "reports" / "daily_brief"

ROBOTICS_COMPANIES = [
    "Tesla / Optimus",
    "NVIDIA ecosystem",
    "UBTECH / Fourier / Unitree",
    "FANUC / Yaskawa / ABB",
]

AI_TRACKS = [
    "papers and reports",
    "LLM and product releases",
    "AI apps and market performance",
]


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_dated_dir(root: Path) -> Path | None:
    if not root.exists():
        return None
    candidates = sorted([p for p in root.iterdir() if p.is_dir()])
    return candidates[-1] if candidates else None


def _resolve_report_dir(root: Path, requested_date: str) -> Path | None:
    if requested_date:
        candidate = root / requested_date
        if candidate.exists():
            return candidate
    return _latest_dated_dir(root)


def _safe_float(value: Any) -> float | None:
    try:
        text = _clean(value)
        if not text:
            return None
        return float(text)
    except ValueError:
        return None


def _model_key(row: dict[str, Any]) -> str:
    return f"{_clean(row.get('车系ID'))}||{_clean(row.get('车型'))}"


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = _load_json(path)
    return payload if isinstance(payload, list) else []


def _latest_news_file(requested_date: str) -> Path | None:
    report_dir = _resolve_report_dir(NEWS_ROOT, requested_date)
    if not report_dir:
        return None
    candidates = sorted(report_dir.glob("daily_market_news_*.json"))
    return candidates[-1] if candidates else None


def _pick_top_ev(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: (
            _safe_float(row.get("高压平台电压(V)")) or 0,
            -(_safe_float(row.get("快充时间(分钟)")) or 9999),
            _safe_float(row.get("纯电续航里程(km)CLTC")) or 0,
            _safe_float(row.get("电池容量(kWh)")) or 0,
        ),
        reverse=True,
    )
    seen: set[str] = set()
    picked: list[dict[str, Any]] = []
    for row in ranked:
        key = _model_key(row)
        if key in seen:
            continue
        seen.add(key)
        picked.append(row)
        if len(picked) >= limit:
            break
    return picked


def _filter_powertrain_rows(rows: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    if mode == "all":
        return rows
    if mode == "nev":
        return [
            row
            for row in rows
            if any(token in _clean(row.get("动力形式")) for token in ["纯电", "增程", "插电", "混动", "油电"])
        ]
    return [row for row in rows if "纯电" in _clean(row.get("动力形式"))]


def _pick_nev_rows(rows: list[dict[str, Any]], limit: int = 4) -> list[dict[str, Any]]:
    nev_rows = [
        row
        for row in rows
        if any(token in _clean(row.get("动力形式")) for token in ["增程", "插电", "混动", "油电"])
    ]
    ranked = sorted(
        nev_rows,
        key=lambda row: (
            _safe_float(row.get("价格(万元)")) or 0,
            _safe_float(row.get("纯电续航里程(km)CLTC")) or 0,
            _safe_float(row.get("电池容量(kWh)")) or 0,
        ),
        reverse=True,
    )
    return ranked[:limit]


def _pick_top_motor(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: (
            _safe_float(row.get("电动机总功率(kW)")) or 0,
            _safe_float(row.get("电动机总马力(Ps)")) or 0,
            _safe_float(row.get("电动机总扭矩(Nm)")) or 0,
        ),
        reverse=True,
    )
    seen: set[str] = set()
    picked: list[dict[str, Any]] = []
    for row in ranked:
        key = _model_key(row)
        if key in seen:
            continue
        seen.add(key)
        picked.append(row)
        if len(picked) >= limit:
            break
    return picked


def _bullet_for_ev(row: dict[str, Any]) -> str:
    model = _clean(row.get("车型")) or "未命名车型"
    range_km = _clean(row.get("纯电续航里程(km)CLTC")) or _clean(row.get("纯电续航里程(km)工信部")) or "n/a"
    voltage = _clean(row.get("高压快充平台")) or "未明确显示"
    charge_time = _clean(row.get("充电时间")) or "未明确显示"
    battery = _clean(row.get("电池容量(kWh)")) or "未明确显示"
    battery_type = _clean(row.get("电池类型")) or "未明确显示"
    highlights = _clean(row.get("亮点标签")) or "未明确显示"
    swap_support = _clean(row.get("换电支持")) or "未明确显示"
    adas = _clean(row.get("ADAS配置")) or "未明确显示"
    return (
        f"{model}: {voltage} fast-charge platform, range {range_km} km, charge window {charge_time}; "
        f"battery {battery} kWh / {battery_type}; highlights {highlights}; swap {swap_support}; ADAS {adas}."
    )


def _bullet_for_motor(row: dict[str, Any]) -> str:
    model = _clean(row.get("车型")) or "未命名车型"
    power_kw = _clean(row.get("电动机总功率(kW)")) or "未明确显示"
    horsepower = _clean(row.get("电动机总马力(Ps)")) or "未明确显示"
    torque = _clean(row.get("电动机总扭矩(Nm)")) or "未明确显示"
    layout = _clean(row.get("电机布局")) or "未明确显示"
    return f"{model}: motor {power_kw} kW / {horsepower} Ps / {torque} Nm, layout {layout}."


def _news_item_to_bullet(item: dict[str, Any]) -> str:
    title = _clean(item.get("title")) or _clean(item.get("link")) or "Untitled item"
    source = _clean(item.get("source")) or "Unknown source"
    market = ", ".join(item.get("markets") or []) if isinstance(item.get("markets"), list) else ""
    themes = ", ".join(item.get("themes") or []) if isinstance(item.get("themes"), list) else ""
    tags = " | ".join([part for part in [market, themes] if part])
    return f"{title} ({source})" + (f" [{tags}]" if tags else "")


def _section_a(charging_rows: list[dict[str, Any]], motor_rows: list[dict[str, Any]], powertrain_mode: str) -> dict[str, Any]:
    scoped_rows = _filter_powertrain_rows(charging_rows, powertrain_mode)
    top_ev = _pick_top_ev(scoped_rows, limit=8)
    top_motor = _pick_top_motor(motor_rows, limit=4)
    top_nev = _pick_nev_rows(charging_rows, limit=4) if powertrain_mode in {"nev", "all"} else []
    bullets = [_bullet_for_ev(row) for row in top_ev]
    bullets.extend(f"NEV focus: {_bullet_for_ev(row)}" for row in top_nev)
    if powertrain_mode in {"nev", "all"} and not top_nev:
        bullets.append("NEV focus: 当前数据集中未识别到增程/插混/油电车型，建议更新全量源或放宽筛选范围。")
    bullets.extend(_bullet_for_motor(row) for row in top_motor)
    trend = {
        "zh": "高压平台与长续航车型仍是主导方向，900V 车型占据亮点位置；电驱性能信息覆盖仍明显落后于充电字段。",
        "en": "High-voltage fast charging and long-range EVs remain the clearest product trend, while motor-side disclosure still lags charging-field completeness.",
    }
    table = [
        {
            "model": _clean(row.get("车型")),
            "brand": _clean(row.get("品牌")),
            "range_km_cltc": _clean(row.get("纯电续航里程(km)CLTC")),
            "platform": _clean(row.get("高压快充平台")),
            "charge_time": _clean(row.get("充电时间")),
            "highlights": _clean(row.get("亮点标签")),
            "swap_support": _clean(row.get("换电支持")),
            "adas": _clean(row.get("ADAS配置")),
            "battery_kwh": _clean(row.get("电池容量(kWh)")),
            "battery_type": _clean(row.get("电池类型")),
        }
        for row in top_ev[:8]
    ]
    return {
        "title": "A. EV / Hybrid Intelligence",
        "title_zh": "A. 新能源汽车 / 混动汽车",
        "items": bullets[:12],
        "table": table,
        "nev_table": [
            {
                "model": _clean(row.get("车型")),
                "powertrain": _clean(row.get("动力形式")),
                "highlights": _clean(row.get("亮点标签")),
                "battery_kwh": _clean(row.get("电池容量(kWh)")),
                "generator_ps": _clean(row.get("发电机马力(Ps)")),
            }
            for row in top_nev
        ],
        "trend": trend,
        "source_health": {
            "charging_rows": len(scoped_rows),
            "motor_rows": len(motor_rows),
            "nev_rows": len(top_nev),
        },
    }


def _theme_priority(item: dict[str, Any], preferred: set[str]) -> tuple[int, int, str]:
    themes = set(item.get("themes") or [])
    overlap = len(themes.intersection(preferred))
    return (-overlap, -len(themes), _clean(item.get("published")) or _clean(item.get("title")))


def _section_b(news_items: list[dict[str, Any]], market_digest: dict[str, Any], quotes: dict[str, Any]) -> dict[str, Any]:
    matched = []
    for item in news_items:
        themes = set(item.get("themes") or [])
        text = json.dumps(item, ensure_ascii=False).lower()
        if themes.intersection({"robotics", "embodied ai", "robotics capital markets", "robotics partnerships"}):
            matched.append(item)
            continue
        if any(keyword in text for keyword in ["robot", "robotics", "humanoid", "embodied", "optimus", "融资", "上市", "机器人"]):
            matched.append(item)
    matched = sorted(matched, key=lambda item: _theme_priority(item, {"robotics", "embodied ai", "robotics capital markets", "robotics partnerships"}))
    bullets = [_news_item_to_bullet(item) for item in matched[:10]]
    fallback_pool = [
        "Track financing, IPO, and strategic partnership changes for humanoid vendors and listed robotics suppliers; current upstream feed returned limited direct hits.",
        "Watch Tesla / Optimus announcements for commercialization cadence, supply-chain expansion, and pilot deployment signals.",
        "Monitor NVIDIA ecosystem partnerships for perception, simulation, training, and embodied-AI compute stack adoption.",
        "Monitor China humanoid players such as UBTECH, Fourier, and Unitree for contract wins, pilot deployments, and policy-linked funding updates.",
        "Industrial robotics incumbents remain relevant for capex signals, factory automation demand, and AI-enabled controller upgrades.",
        "Look for project-level disclosures involving automotive, warehousing, logistics, and smart-manufacturing robot deployments.",
        "Separate balance-sheet events from technical progress so funding news does not obscure product readiness.",
        "Use listed suppliers and ecosystem partners as proxy indicators when private robotics companies disclose little primary data.",
    ]
    if len(bullets) < 8:
        bullets.extend(fallback_pool[: max(0, 8 - len(bullets))])
    digest_sections = market_digest.get("sections") or []
    robotics_signal = next((section for section in digest_sections if section.get("category") == "robotics"), {})
    trend = {
        "zh": "机器人板块需要更强的专用主题源；现阶段可先借助 AI 算力与市场新闻作弱信号补充。",
        "en": "Robotics coverage still needs dedicated topic sources; for now, AI-compute market signals can only serve as weak secondary evidence.",
    }
    return {
        "title": "B. Robotics / Embodied AI",
        "title_zh": "B. 机器人 / 具身智能",
        "items": bullets[:12],
        "watchlist": ROBOTICS_COMPANIES,
        "market_signal": {
            "summary": _clean(robotics_signal.get("summary")) or "No robotics market summary available.",
            "quotes_status": quotes.get("meta", {}).get("status", "unknown"),
        },
        "trend": trend,
    }


def _section_c(news_items: list[dict[str, Any]], news_payload: dict[str, Any]) -> dict[str, Any]:
    matched = []
    for item in news_items:
        themes = set(item.get("themes") or [])
        text = json.dumps(item, ensure_ascii=False).lower()
        if themes.intersection({"llm releases", "ai papers", "ai apps", "ai paradigm", "ai compute"}):
            matched.append(item)
            continue
        if any(keyword in text for keyword in ["llm", "gpt", "claude", "gemini", "paper", "report", "model", "agent", "应用", "论文", "报告"]):
            matched.append(item)
    matched = sorted(matched, key=lambda item: _theme_priority(item, {"llm releases", "ai papers", "ai apps", "ai paradigm", "ai compute"}))
    bullets = [_news_item_to_bullet(item) for item in matched[:10]]
    fallback_pool = [
        "Track major LLM release cadence across OpenAI, Anthropic, Google, and open-source foundation model ecosystems.",
        "Separate academic paradigm shifts from product launches so paper-driven capability changes do not get lost in release noise.",
        "Add application-layer performance signals such as ranking, enterprise adoption, and monetization where market data is available.",
        "Maintain a dual-track view: technical paradigm shifts and commercial distribution outcomes.",
        "Watch for multimodal and agentic capability updates that materially change AI product design assumptions.",
        "Capture new papers and reports as paradigm evidence, not just as link dumps; emphasize inference cost, data efficiency, and tool use.",
        "Track ecosystem-level downstream adoption in coding, enterprise copilots, search, and vertical workflow automation.",
        "Compare release headlines with actual market traction so version noise does not dominate the daily brief.",
    ]
    if len(bullets) < 8:
        bullets.extend(fallback_pool[: max(0, 8 - len(bullets))])
    trend = {
        "zh": "AI 板块需要补入更直接的论文与模型发布源；当前市场新闻流水线可以先承担通用新闻骨架。",
        "en": "AI coverage still needs direct paper and model-release sources; the current market-news pipeline is sufficient only as a general-news backbone.",
    }
    return {
        "title": "C. AI Research and Market",
        "title_zh": "C. AI 研究与市场",
        "items": bullets[:12],
        "tracks": AI_TRACKS,
        "news_meta": {
            "mode": news_payload.get("mode", ""),
            "markets": news_payload.get("markets", []),
            "item_count": news_payload.get("item_count", 0),
            "failure_count": len(news_payload.get("failures") or []),
        },
        "trend": trend,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Daily EV / Robotics / AI Brief",
        "",
        f"- Run date / 运行日期: {payload['run_date']}",
        f"- Generated at / 生成时间: {payload['generated_at']}",
        f"- Powertrain mode / 动力模式: {payload.get('powertrain_mode', 'pure_ev')}",
        f"- Freshness / 数据新鲜度: charging={payload['freshness']['charging_date']}, motor={payload['freshness']['motor_date']}, news={payload['freshness']['news_date']}, market_watch={payload['freshness']['market_watch_date']}",
        "",
    ]

    for key in ["section_a", "section_b", "section_c"]:
        section = payload[key]
        lines.append(f"## {section['title_zh']} / {section['title']}")
        lines.append("")
        for item in section["items"]:
            lines.append(f"- {item}")
        lines.append("")
        if key == "section_a":
            lines.append("### Key Table / 核心表")
            lines.append("")
            lines.append("| Model | Brand | CLTC km | Platform | Charge Time | Highlights | Swap | ADAS | Battery kWh | Battery Type |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
            for row in section["table"]:
                lines.append(
                    "| {model} | {brand} | {range_km_cltc} | {platform} | {charge_time} | {highlights} | {swap_support} | {adas} | {battery_kwh} | {battery_type} |".format(**row)
                )
            lines.append("")
            if payload.get("powertrain_mode") in {"nev", "all"}:
                lines.append("### NEV / Hybrid Subgroup / 混动与增程分组")
                lines.append("")
                lines.append("| Model | Powertrain | Highlights | Battery kWh | Generator Ps |")
                lines.append("| --- | --- | --- | --- | --- |")
                if section.get("nev_table"):
                    for row in section["nev_table"]:
                        lines.append(
                            "| {model} | {powertrain} | {highlights} | {battery_kwh} | {generator_ps} |".format(**row)
                        )
                else:
                    lines.append("| (no NEV rows in current artifact) | - | - | - | - |")
                lines.append("")
        lines.append(f"Trend / 趋势: {section['trend']['zh']} {section['trend']['en']}")
        lines.append("")

    lines.append("## Source Health / 来源健康度")
    lines.append("")
    for warning in payload["source_health"]["warnings"]:
        lines.append(f"- {warning}")
    if not payload["source_health"]["warnings"]:
        lines.append("- All upstream sources delivered usable artifacts.")
    lines.append("")
    return "\n".join(lines)


def _render_html(payload: dict[str, Any]) -> str:
    body = [
        f"<h1>Daily EV / Robotics / AI Brief</h1>",
        f"<p><strong>Run date:</strong> {html.escape(payload['run_date'])}<br/>"
        f"<strong>Generated at:</strong> {html.escape(payload['generated_at'])}<br/>"
        f"<strong>Powertrain mode:</strong> {html.escape(payload.get('powertrain_mode', 'pure_ev'))}</p>",
    ]
    for key in ["section_a", "section_b", "section_c"]:
        section = payload[key]
        body.append(f"<h2>{html.escape(section['title_zh'])} / {html.escape(section['title'])}</h2>")
        body.append("<ul>")
        for item in section["items"]:
            body.append(f"<li>{html.escape(item)}</li>")
        body.append("</ul>")
        if key == "section_a" and payload.get("powertrain_mode") in {"nev", "all"}:
            body.append("<h3>NEV / Hybrid Subgroup</h3>")
            body.append("<table><thead><tr><th>Model</th><th>Powertrain</th><th>Highlights</th><th>Battery kWh</th><th>Generator Ps</th></tr></thead><tbody>")
            if section.get("nev_table"):
                for row in section["nev_table"]:
                    body.append(
                        "<tr>"
                        f"<td>{html.escape(row.get('model', ''))}</td>"
                        f"<td>{html.escape(row.get('powertrain', ''))}</td>"
                        f"<td>{html.escape(row.get('highlights', ''))}</td>"
                        f"<td>{html.escape(row.get('battery_kwh', ''))}</td>"
                        f"<td>{html.escape(row.get('generator_ps', ''))}</td>"
                        "</tr>"
                    )
            else:
                body.append("<tr><td>(no NEV rows in current artifact)</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>")
            body.append("</tbody></table>")
        body.append(f"<p><strong>Trend:</strong> {html.escape(section['trend']['zh'])} {html.escape(section['trend']['en'])}</p>")
    body.append("<h2>Source Health / 来源健康度</h2>")
    body.append("<ul>")
    warnings = payload["source_health"]["warnings"] or ["All upstream sources delivered usable artifacts."]
    for warning in warnings:
        body.append(f"<li>{html.escape(warning)}</li>")
    body.append("</ul>")
    return "\n".join(body)


def build_payload(run_date: str) -> tuple[dict[str, Any], Path]:
    return build_payload_for_mode(run_date, "pure_ev")


def build_payload_for_mode(run_date: str, powertrain_mode: str) -> tuple[dict[str, Any], Path]:
    charging_dir = _resolve_report_dir(CHARGING_ROOT, run_date)
    motor_dir = _resolve_report_dir(MOTOR_ROOT, run_date)
    news_file = _latest_news_file(run_date)

    if not charging_dir:
        raise FileNotFoundError("No charging report directory found.")
    if not motor_dir:
        raise FileNotFoundError("No motor report directory found.")
    if not news_file:
        raise FileNotFoundError("No daily market news report found.")

    charging_rows = _load_rows(charging_dir / "filtered.json")
    motor_rows = _load_rows(motor_dir / "filtered.json")
    news_payload = _load_json(news_file)
    news_items = news_payload.get("items") or []
    market_digest = _load_json(MARKET_WATCH_ROOT / "digest" / "latest_digest.json")
    quotes_payload = _load_json(MARKET_WATCH_ROOT / "quotes_latest.json")

    warnings: list[str] = []
    if not charging_rows:
        warnings.append("Charging artifact exists but contains no rows.")
    if not motor_rows:
        warnings.append("Motor artifact exists but contains no rows.")
    if not news_items:
        warnings.append("Daily market news returned no items; downstream sections include fallback guidance.")
    if quotes_payload.get("meta", {}).get("status") == "degraded":
        warnings.append("Market watch quotes are degraded; use trend text as qualitative only.")

    resolved_run_date = run_date or _clean(charging_rows[0].get("数据日期")) or dt.date.today().isoformat()
    payload = {
        "run_date": resolved_run_date,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "freshness": {
            "charging_date": charging_dir.name,
            "motor_date": motor_dir.name,
            "news_date": news_payload.get("date", news_file.parent.name),
            "market_watch_date": quotes_payload.get("meta", {}).get("snapshot_date", ""),
        },
        "powertrain_mode": powertrain_mode,
        "section_a": _section_a(charging_rows, motor_rows, powertrain_mode),
        "section_b": _section_b(news_items, market_digest, quotes_payload),
        "section_c": _section_c(news_items, news_payload),
        "trend_7d": {
            "zh": "首版仅输出定性趋势，后续接入最近 7 天滚动对比。",
            "en": "Initial release provides qualitative trend text only; rolling 7-day comparisons come next.",
        },
        "trend_30d": {
            "zh": "首版保留 30 天趋势占位，后续在多日产物积累后启用。",
            "en": "Initial release keeps a 30-day trend placeholder until enough daily artifacts accumulate.",
        },
        "source_health": {
            "warnings": warnings,
            "news_failures": news_payload.get("failures", []),
            "market_sources": quotes_payload.get("meta", {}).get("source_status", []),
        },
    }
    output_dir = OUT_ROOT / resolved_run_date
    return payload, output_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a unified daily brief from existing EV, robotics, and AI artifacts.")
    parser.add_argument("--date", default="", help="Preferred date in YYYY-MM-DD. Falls back to latest available per upstream source.")
    parser.add_argument("--powertrain-mode", choices=["pure_ev", "nev", "all"], default="pure_ev", help="How section A should scope EV/NEV rows.")
    parser.add_argument("--dry-run", action="store_true", help="Build payload and print summary without writing files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload, output_dir = build_payload_for_mode(args.date, args.powertrain_mode)
    markdown = _render_markdown(payload)
    section_html = _render_html(payload)

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        date_str = payload["run_date"]
        (output_dir / f"daily_brief_{date_str}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (output_dir / f"daily_brief_{date_str}.md").write_text(markdown + "\n", encoding="utf-8")
        (output_dir / "confluence_section.html").write_text(section_html + "\n", encoding="utf-8")

    print(f"Run date: {payload['run_date']}")
    print(f"Charging date: {payload['freshness']['charging_date']}")
    print(f"Motor date: {payload['freshness']['motor_date']}")
    print(f"News date: {payload['freshness']['news_date']}")
    print(f"Market watch date: {payload['freshness']['market_watch_date']}")
    print(f"Section A items: {len(payload['section_a']['items'])}")
    print(f"Section B items: {len(payload['section_b']['items'])}")
    print(f"Section C items: {len(payload['section_c']['items'])}")
    print(f"Warnings: {len(payload['source_health']['warnings'])}")
    if not args.dry_run:
        print(f"Output: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
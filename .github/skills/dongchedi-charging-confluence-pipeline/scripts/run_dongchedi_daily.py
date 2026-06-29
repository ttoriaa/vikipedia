from __future__ import annotations

import argparse
import csv
import datetime as dt
import glob
import html
import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from refresh_dongchedi_source import refresh_source_csv


def _resolve_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "reports").exists() and (parent / "dongchedi_price_map.csv").exists():
            return parent
    # Fallback keeps legacy behavior if repository markers are unavailable.
    return p.parents[1]


ROOT = _resolve_root()
REPORT_ROOT = ROOT / "reports" / "dongchedi_daily"
PRICE_MAP_DEFAULT = ROOT / "dongchedi_price_map.csv"

OUTPUT_COLUMNS = [
    "数据日期",
    "车系ID",
    "车型",
    "品牌",
    "动力形式",
    "价格(万元)",
    "亮点标签",
    "6C快充标签",
    "换电支持",
    "ADAS配置",
    "纯电续航里程(km)工信部",
    "纯电续航里程(km)CLTC",
    "电池能量密度(Wh/kg)",
    "高压快充平台",
    "充电时间",
    "快充时间(分钟)",
    "充电电量",
    "快充窗口跨度(%)",
    "高压平台电压(V)",
    "电池容量(kWh)",
    "电芯品牌",
    "电池类型",
    "电动机",
    "电控系统",
    "发电机马力(Ps)",
    "缺失状态",
    "数据状态",
]

KEY_FIELDS_FOR_MISSING = ["高压快充平台", "充电时间", "充电电量", "电池容量(kWh)", "电芯品牌", "电池类型", "换电支持", "ADAS配置"]


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _model_key(row: dict[str, str]) -> str:
    return f"{_clean(row.get('车系ID'))}||{_clean(row.get('车型'))}"


def _brand_name(model_name: str) -> str:
    name = _clean(model_name)
    if not name:
        return "未明确显示"

    eng = re.match(r"[A-Za-z][A-Za-z0-9\-#]*", name)
    if eng:
        return eng.group(0)

    # Works for strings like "品牌品牌车型" and "品牌车型"
    for i in range(2, min(8, len(name) // 2 + 1)):
        if name[:i] == name[i : 2 * i]:
            return name[:i]

    token = re.split(r"[\sA-Za-z0-9#\-\+\(\)]", name, maxsplit=1)[0].strip()
    return token or name[:2]


def _is_missing(value: str) -> bool:
    v = _clean(value)
    return not v or v == "未明确显示"


def _parse_price_wan(text: str) -> float | None:
    t = _clean(text)
    if not t:
        return None

    # Keep only number-like content; support ranges like 25.99-29.99.
    nums = re.findall(r"\d+(?:\.\d+)?", t)
    if not nums:
        return None
    try:
        return float(nums[0])
    except ValueError:
        return None


def _parse_price_floor_wan(text: str) -> float | None:
    t = _clean(text)
    if not t:
        return None

    nums = re.findall(r"\d+(?:\.\d+)?", t)
    if not nums:
        return None
    try:
        return float(nums[0])
    except ValueError:
        return None


def _extract_first_number(text: str) -> float | None:
    t = _clean(text)
    if not t:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", t)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _parse_fast_charge_minutes(charge_time_text: str) -> float | None:
    t = _clean(charge_time_text)
    if not t or t == "未明确显示":
        return None

    m = re.search(r"快充\s*(\d+(?:\.\d+)?)\s*分钟", t)
    if m:
        return float(m.group(1))

    # If no explicit fast-charge marker exists, fallback to first minute value.
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*分钟", t)
    if m2:
        return float(m2.group(1))
    return None


def _parse_charge_window_span(charge_window_text: str) -> float | None:
    t = _clean(charge_window_text)
    if not t or t == "未明确显示":
        return None

    nums = re.findall(r"\d+(?:\.\d+)?", t)
    if len(nums) < 2:
        return None
    try:
        lo = float(nums[0])
        hi = float(nums[1])
        return max(0.0, hi - lo)
    except ValueError:
        return None


def _parse_platform_voltage(platform_text: str) -> float | None:
    t = _clean(platform_text)
    if not t or t == "未明确显示":
        return None
    m = re.search(r"(\d{3,4})\s*V", t, flags=re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def _infer_powertrain_scope(power_text: str, mode: str) -> bool:
    power = _clean(power_text)
    if mode == "all":
        return True
    if mode == "nev":
        return any(token in power for token in ["纯电", "增程", "插电", "混动", "油电"])
    return "纯电" in power


def _infer_6c_tag(platform_text: str, charge_time_text: str, model_name: str) -> str:
    combined = " ".join([_clean(platform_text), _clean(charge_time_text), _clean(model_name)]).lower()
    if "6c" in combined:
        return "6C"
    fast_minutes = _parse_fast_charge_minutes(charge_time_text)
    if fast_minutes is not None and fast_minutes <= 10:
        return "疑似6C级快充"
    return "未明确显示"


def _infer_swap_support(row: dict[str, str], model_name: str) -> str:
    source_value = _clean(row.get("换电支持")) or _clean(row.get("换电"))
    if source_value:
        return source_value
    combined = f"{_clean(model_name)} {_clean(row.get('品牌'))}"
    if any(token in combined for token in ["乐道", "蔚来", "firefly", "萤火虫"]):
        return "支持换电"
    return "未明确显示"


def _infer_adas(row: dict[str, str], model_name: str) -> str:
    source_value = _clean(row.get("ADAS配置")) or _clean(row.get("辅助驾驶")) or _clean(row.get("智能辅助驾驶"))
    if source_value:
        return source_value
    combined = " ".join([model_name, _clean(row.get("车型")), _clean(row.get("动力形式"))])
    tags = []
    if any(token in combined for token in ["激光雷达", "城区辅助驾驶", "智驾", "乾崑", "辅助驾驶"]):
        tags.append("高阶辅助驾驶线索")
    if any(token in combined for token in ["Max", "Ultra", "旗舰"]):
        tags.append("高配智驾版本线索")
    return " / ".join(tags) if tags else "未明确显示"


def _infer_highlight_tags(row: dict[str, str], model_name: str, platform_text: str, charge_time_text: str) -> str:
    tags: list[str] = []
    voltage = _parse_platform_voltage(platform_text)
    fast_minutes = _parse_fast_charge_minutes(charge_time_text)
    range_cltc = _extract_first_number(_clean(row.get("纯电续航里程(km)CLTC")) or _clean(row.get("纯电续航里程(km)工信部")))
    tag_6c = _infer_6c_tag(platform_text, charge_time_text, model_name)
    swap_support = _infer_swap_support(row, model_name)
    adas = _infer_adas(row, model_name)
    if voltage is not None and voltage >= 800:
        tags.append("800V+")
    if tag_6c != "未明确显示":
        tags.append(tag_6c)
    if fast_minutes is not None and fast_minutes <= 12:
        tags.append("超充<=12分钟")
    if range_cltc is not None and range_cltc >= 700:
        tags.append("长续航700+")
    if swap_support != "未明确显示":
        tags.append("换电")
    if adas != "未明确显示":
        tags.append("ADAS")
    if "增程" in _clean(row.get("动力形式")):
        tags.append("增程")
    if "插电" in _clean(row.get("动力形式")) or "混动" in _clean(row.get("动力形式")):
        tags.append("混动")
    return "、".join(dict.fromkeys(tags)) if tags else "未明确显示"


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict((k, _clean(v)) for k, v in row.items()) for row in csv.DictReader(f)]


def _find_latest_source(source_override: str | None) -> Path:
    if source_override:
        p = Path(source_override)
        if not p.is_absolute():
            p = ROOT / p
        if not p.exists():
            raise FileNotFoundError(f"Source CSV not found: {p}")
        return p

    candidates = sorted(glob.glob(str(ROOT / "dongchedi_full_configs_*.csv")))
    if not candidates:
        raise FileNotFoundError("No source CSV found. Expected dongchedi_full_configs_YYYY-MM-DD.csv in workspace root.")
    return Path(candidates[-1])


def _load_price_map(price_map_path: Path) -> tuple[dict[tuple[str, str], float], dict[str, float]]:
    if not price_map_path.exists():
        return {}, {}

    rows = _load_csv_rows(price_map_path)
    pair_map: dict[tuple[str, str], float] = {}
    series_map: dict[str, float] = {}

    for r in rows:
        sid = _clean(r.get("车系ID"))
        model = _clean(r.get("车型"))
        price_text = _clean(r.get("价格(万元)"))
        price = _parse_price_floor_wan(price_text)
        if price is None:
            continue
        if sid and model:
            pair_map[(sid, model)] = price
        if sid:
            series_map[sid] = price

    return pair_map, series_map


def _create_price_map_template(path: Path, source_rows: list[dict[str, str]]) -> None:
    uniq: dict[tuple[str, str], None] = {}
    for r in source_rows:
        sid = _clean(r.get("车系ID"))
        model = _clean(r.get("车型"))
        if sid and model:
            uniq[(sid, model)] = None

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["车系ID", "车型", "价格(万元)", "价格来源", "更新时间"])
        writer.writeheader()
        for sid, model in sorted(uniq.keys()):
            writer.writerow(
                {
                    "车系ID": sid,
                    "车型": model,
                    "价格(万元)": "",
                    "价格来源": "手动维护",
                    "更新时间": "",
                }
            )


def _find_latest_previous_report(run_date: str) -> Path | None:
    if not REPORT_ROOT.exists():
        return None

    previous_dirs = [p for p in REPORT_ROOT.iterdir() if p.is_dir() and p.name < run_date]
    if not previous_dirs:
        return None

    latest_dir = sorted(previous_dirs)[-1]
    candidate = latest_dir / "filtered.json"
    if not candidate.exists():
        return None
    return candidate


def _load_previous_rows(run_date: str) -> list[dict[str, str]]:
    prev = _find_latest_previous_report(run_date)
    if not prev:
        return []
    return json.loads(prev.read_text(encoding="utf-8"))


def _resolve_price(
    row: dict[str, str],
    pair_map: dict[tuple[str, str], float],
    series_map: dict[str, float],
    source_price_cols: list[str],
) -> float | None:
    sid = _clean(row.get("车系ID"))
    model = _clean(row.get("车型"))

    if sid and model and (sid, model) in pair_map:
        return pair_map[(sid, model)]
    if sid in series_map:
        return series_map[sid]

    for c in source_price_cols:
        v = _parse_price_wan(_clean(row.get(c)))
        if v is not None:
            return v

    return None


def _missing_status(row: dict[str, str]) -> str:
    missing = [field for field in KEY_FIELDS_FOR_MISSING if _is_missing(row.get(field, ""))]
    if not missing:
        return "完整"
    return "缺失:" + "、".join(missing)


def _to_output_row(row: dict[str, str], run_date: str, price_wan: float, data_status: str) -> dict[str, str]:
    model_name = _clean(row.get("车型"))
    charge_time_text = _clean(row.get("充电时间")) or "未明确显示"
    charge_window_text = _clean(row.get("充电电量")) or _clean(row.get("快充电量(%)")) or "未明确显示"
    platform_text = _clean(row.get("高压快充平台")) or "未明确显示"
    adas_text = _infer_adas(row, model_name)
    swap_support = _infer_swap_support(row, model_name)
    six_c_tag = _infer_6c_tag(platform_text, charge_time_text, model_name)
    highlight_tags = _infer_highlight_tags(row, model_name, platform_text, charge_time_text)

    fast_minutes = _parse_fast_charge_minutes(charge_time_text)
    charge_window_span = _parse_charge_window_span(charge_window_text)
    platform_voltage = _parse_platform_voltage(platform_text)

    return {
        "数据日期": run_date,
        "车系ID": _clean(row.get("车系ID")),
        "车型": model_name,
        "品牌": _brand_name(model_name),
        "动力形式": _clean(row.get("动力形式")) or "纯电动",
        "价格(万元)": f"{price_wan:.2f}",
        "亮点标签": highlight_tags,
        "6C快充标签": six_c_tag,
        "换电支持": swap_support,
        "ADAS配置": adas_text,
        "纯电续航里程(km)工信部": _clean(row.get("纯电续航里程(km)工信部")) or "未明确显示",
        "纯电续航里程(km)CLTC": _clean(row.get("纯电续航里程(km)CLTC")) or "未明确显示",
        "电池能量密度(Wh/kg)": _clean(row.get("电池能量密度(Wh/kg)")) or "未明确显示",
        "高压快充平台": platform_text,
        "充电时间": charge_time_text,
        "快充时间(分钟)": f"{fast_minutes:.1f}" if fast_minutes is not None else "未明确显示",
        "充电电量": charge_window_text,
        "快充窗口跨度(%)": f"{charge_window_span:.1f}" if charge_window_span is not None else "未明确显示",
        "高压平台电压(V)": f"{platform_voltage:.0f}" if platform_voltage is not None else "未明确显示",
        "电池容量(kWh)": _clean(row.get("电池容量(kWh)")) or "未明确显示",
        "电芯品牌": _clean(row.get("电芯品牌")) or "未明确显示",
        "电池类型": _clean(row.get("电池类型")) or "未明确显示",
        "电动机": _clean(row.get("电动机")) or "未明确显示",
        "电控系统": _clean(row.get("电控系统")) or _clean(row.get("电控")) or "未明确显示",
        "发电机马力(Ps)": _clean(row.get("发电机马力(Ps)")) or _clean(row.get("发电机马力")) or "未明确显示",
        "缺失状态": "",
        "数据状态": data_status,
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def _build_diff(current_rows: list[dict[str, str]], previous_rows: list[dict[str, str]]) -> dict[str, Any]:
    cur = {_model_key(r): r for r in current_rows}
    prev = {_model_key(r): r for r in previous_rows}

    added = sorted(k for k in cur.keys() if k not in prev)
    removed = sorted(k for k in prev.keys() if k not in cur)

    improved = 0
    for k in sorted(set(cur.keys()) & set(prev.keys())):
        prev_missing = sum(1 for f in KEY_FIELDS_FOR_MISSING if _is_missing(prev[k].get(f, "")))
        cur_missing = sum(1 for f in KEY_FIELDS_FOR_MISSING if _is_missing(cur[k].get(f, "")))
        if cur_missing < prev_missing:
            improved += 1

    return {
        "added_count": len(added),
        "removed_count": len(removed),
        "improved_count": improved,
        "added_models": added,
        "removed_models": removed,
    }


def _rows_to_markdown(rows: list[dict[str, str]]) -> str:
    headers = [
        "车系ID",
        "品牌",
        "车型",
        "价格(万元)",
        "亮点标签",
        "6C快充标签",
        "换电支持",
        "ADAS配置",
        "纯电续航里程(km)工信部",
        "纯电续航里程(km)CLTC",
        "电池能量密度(Wh/kg)",
        "高压快充平台",
        "充电时间",
        "快充时间(分钟)",
        "充电电量",
        "快充窗口跨度(%)",
        "高压平台电压(V)",
        "电池容量(kWh)",
        "电芯品牌",
        "电池类型",
        "电动机",
        "电控系统",
        "发电机马力(Ps)",
        "缺失状态",
        "数据状态",
    ]

    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]

    for r in rows:
        vals = [r.get(h, "") for h in headers]
        safe = [v.replace("\n", " ").replace("|", "/") for v in vals]
        lines.append("| " + " | ".join(safe) + " |")

    return "\n".join(lines)


def _rows_to_html_table(rows: list[dict[str, str]]) -> str:
    headers = [
        "车系ID",
        "品牌",
        "车型",
        "价格(万元)",
        "亮点标签",
        "6C快充标签",
        "换电支持",
        "ADAS配置",
        "纯电续航里程(km)工信部",
        "纯电续航里程(km)CLTC",
        "电池能量密度(Wh/kg)",
        "高压快充平台",
        "充电时间",
        "快充时间(分钟)",
        "充电电量",
        "快充窗口跨度(%)",
        "高压平台电压(V)",
        "电池容量(kWh)",
        "电芯品牌",
        "电池类型",
        "电动机",
        "电控系统",
        "发电机马力(Ps)",
        "缺失状态",
        "数据状态",
    ]

    thead = "<tr>" + "".join(f"<th>{html.escape(h)}</th>" for h in headers) + "</tr>"
    body_rows = []
    for r in rows:
        tds = "".join(f"<td>{html.escape(_clean(r.get(h)).replace(chr(10), ' ') )}</td>" for h in headers)
        body_rows.append(f"<tr>{tds}</tr>")

    return f"<table><thead>{thead}</thead><tbody>{''.join(body_rows)}</tbody></table>"


def _html_table(rows: list[dict[str, str]], headers: list[str]) -> str:
    thead = "<tr>" + "".join(f"<th>{html.escape(h)}</th>" for h in headers) + "</tr>"
    body_rows = []
    for r in rows:
        tds = "".join(f"<td>{html.escape(_clean(r.get(h)).replace(chr(10), ' '))}</td>" for h in headers)
        body_rows.append(f"<tr>{tds}</tr>")
    return f"<table><thead>{thead}</thead><tbody>{''.join(body_rows)}</tbody></table>"


def _build_daily_section_html(
    run_date: str,
    source_file: Path,
    current_rows: list[dict[str, str]],
    diff: dict[str, Any],
    unresolved_price_count: int,
) -> str:
    complete_count = sum(1 for r in current_rows if r.get("缺失状态") == "完整")
    carried_count = sum(1 for r in current_rows if r.get("数据状态") != "当日采集")

    table_html = _rows_to_html_table(current_rows)
    summary_html = _build_summary_blocks_html(current_rows)

    return (
        f"<!-- DONGCHEDI_DAILY:{run_date}:START -->"
        f"<h2>懂车帝充电日报 {html.escape(run_date)}</h2>"
        f"<p>数据源: {html.escape(source_file.name)}</p>"
        f"<p>筛选规则: 价格&gt;20万 且 纯电车型；缺失字段车型持续跟踪。</p>"
        f"<ul>"
        f"<li>当日总车型: {len(current_rows)}</li>"
        f"<li>字段完整车型: {complete_count}</li>"
        f"<li>昨日沿用车型: {carried_count}</li>"
        f"<li>新增车型: {diff['added_count']}</li>"
        f"<li>移除车型: {diff['removed_count']}</li>"
        f"<li>缺失转完整: {diff['improved_count']}</li>"
        f"<li>价格缺失(未纳入当日筛选): {unresolved_price_count}</li>"
        f"</ul>"
        f"{summary_html}"
        f"{table_html}"
        f"<!-- DONGCHEDI_DAILY:{run_date}:END -->"
    )


def _to_num(row: dict[str, str], field: str) -> float | None:
    return _extract_first_number(row.get(field, ""))


def _brand_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    bucket: dict[str, dict[str, Any]] = {}
    for r in rows:
        brand = _clean(r.get("品牌")) or "未明确显示"
        b = bucket.setdefault(brand, {"count": 0, "fast": [], "range": [], "capacity": []})
        b["count"] += 1
        f = _to_num(r, "快充时间(分钟)")
        rr = _to_num(r, "纯电续航里程(km)CLTC")
        cap = _to_num(r, "电池容量(kWh)")
        if f is not None:
            b["fast"].append(f)
        if rr is not None:
            b["range"].append(rr)
        if cap is not None:
            b["capacity"].append(cap)

    out: list[dict[str, str]] = []
    for brand, data in sorted(bucket.items(), key=lambda x: (-x[1]["count"], x[0])):
        out.append(
            {
                "品牌": brand,
                "车型数": str(data["count"]),
                "平均快充时间(分钟)": f"{sum(data['fast']) / len(data['fast']):.1f}" if data["fast"] else "未明确显示",
                "平均CLTC续航(km)": f"{sum(data['range']) / len(data['range']):.0f}" if data["range"] else "未明确显示",
                "平均电池容量(kWh)": f"{sum(data['capacity']) / len(data['capacity']):.1f}" if data["capacity"] else "未明确显示",
            }
        )
    return out


def _top_bottom(rows: list[dict[str, str]], field: str, top_n: int = 5, reverse: bool = True) -> list[dict[str, str]]:
    scored = []
    for r in rows:
        v = _to_num(r, field)
        if v is not None:
            scored.append((v, r))
    scored.sort(key=lambda x: x[0], reverse=reverse)
    return [x[1] for x in scored[:top_n]]


def _markdown_table(rows: list[dict[str, str]], headers: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        vals = [str(r.get(h, "")).replace("\n", " ").replace("|", "/") for h in headers]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def _build_summary_blocks(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "## 摘要结论\n\n暂无数据。\n"

    count_all = len(rows)
    with_800v = sum(1 for r in rows if (_to_num(r, "高压平台电压(V)") or 0) >= 800)
    avg_fast = [(_to_num(r, "快充时间(分钟)")) for r in rows]
    avg_fast = [x for x in avg_fast if x is not None]

    best_fast = _top_bottom(rows, "快充时间(分钟)", top_n=5, reverse=False)
    bottom_fast = _top_bottom(rows, "快充时间(分钟)", top_n=5, reverse=True)
    top_range = _top_bottom(rows, "纯电续航里程(km)CLTC", top_n=5, reverse=True)
    bottom_range = _top_bottom(rows, "纯电续航里程(km)CLTC", top_n=5, reverse=False)
    top_density = _top_bottom(rows, "电池能量密度(Wh/kg)", top_n=5, reverse=True)
    brand_rows = _brand_summary(rows)

    text = []
    text.append("## 摘要结论")
    text.append("")
    text.append(f"- 在售样本车型: {count_all}")
    text.append(f"- 800V及以上平台车型: {with_800v} ({with_800v / count_all * 100:.1f}%)")
    text.append(f"- 平均快充时间(分钟): {sum(avg_fast) / len(avg_fast):.1f}" if avg_fast else "- 平均快充时间(分钟): 未明确显示")
    text.append(f"- 带换电标签车型: {sum(1 for r in rows if not _is_missing(r.get('换电支持', '')) and '未明确' not in _clean(r.get('换电支持', '')))}")
    text.append(f"- 带ADAS标签车型: {sum(1 for r in rows if not _is_missing(r.get('ADAS配置', '')) and '未明确' not in _clean(r.get('ADAS配置', '')))}")
    text.append("")

    text.append("## 品牌分组")
    text.append("")
    text.append(_markdown_table(brand_rows, ["品牌", "车型数", "平均快充时间(分钟)", "平均CLTC续航(km)", "平均电池容量(kWh)"]))
    text.append("")

    def pick_rows(src: list[dict[str, str]], metric: str) -> str:
        mini = []
        for r in src:
            mini.append({
                "车系ID": r.get("车系ID", ""),
                "品牌": r.get("品牌", ""),
                "车型": r.get("车型", ""),
                metric: r.get(metric, ""),
                "高压快充平台": r.get("高压快充平台", ""),
                "电池容量(kWh)": r.get("电池容量(kWh)", ""),
            })
        return _markdown_table(mini, ["车系ID", "品牌", "车型", metric, "高压快充平台", "电池容量(kWh)"])

    text.append("## Top/Bottom 对比")
    text.append("")
    text.append("### Top 5 最快快充（分钟越小越好）")
    text.append("")
    text.append(pick_rows(best_fast, "快充时间(分钟)"))
    text.append("")
    text.append("### Bottom 5 最慢快充（分钟越大越慢）")
    text.append("")
    text.append(pick_rows(bottom_fast, "快充时间(分钟)"))
    text.append("")
    text.append("### Top 5 CLTC续航")
    text.append("")
    text.append(pick_rows(top_range, "纯电续航里程(km)CLTC"))
    text.append("")
    text.append("### Bottom 5 CLTC续航")
    text.append("")
    text.append(pick_rows(bottom_range, "纯电续航里程(km)CLTC"))
    text.append("")
    text.append("### Top 5 电池能量密度")
    text.append("")
    text.append(pick_rows(top_density, "电池能量密度(Wh/kg)"))
    text.append("")

    return "\n".join(text)


def _build_summary_blocks_html(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "<h3>摘要结论</h3><p>暂无数据。</p>"

    count_all = len(rows)
    with_800v = sum(1 for r in rows if (_to_num(r, "高压平台电压(V)") or 0) >= 800)
    avg_fast = [(_to_num(r, "快充时间(分钟)")) for r in rows]
    avg_fast = [x for x in avg_fast if x is not None]

    best_fast = _top_bottom(rows, "快充时间(分钟)", top_n=5, reverse=False)
    bottom_fast = _top_bottom(rows, "快充时间(分钟)", top_n=5, reverse=True)
    top_range = _top_bottom(rows, "纯电续航里程(km)CLTC", top_n=5, reverse=True)
    bottom_range = _top_bottom(rows, "纯电续航里程(km)CLTC", top_n=5, reverse=False)
    top_density = _top_bottom(rows, "电池能量密度(Wh/kg)", top_n=5, reverse=True)
    brand_rows = _brand_summary(rows)

    blocks: list[str] = []
    blocks.append("<h3>摘要结论</h3>")
    blocks.append("<ul>")
    blocks.append(f"<li>在售样本车型: {count_all}</li>")
    blocks.append(f"<li>800V及以上平台车型: {with_800v} ({with_800v / count_all * 100:.1f}%)</li>")
    if avg_fast:
        blocks.append(f"<li>平均快充时间(分钟): {sum(avg_fast) / len(avg_fast):.1f}</li>")
    else:
        blocks.append("<li>平均快充时间(分钟): 未明确显示</li>")
    blocks.append(f"<li>带换电标签车型: {sum(1 for r in rows if not _is_missing(r.get('换电支持', '')) and '未明确' not in _clean(r.get('换电支持', '')))}</li>")
    blocks.append(f"<li>带ADAS标签车型: {sum(1 for r in rows if not _is_missing(r.get('ADAS配置', '')) and '未明确' not in _clean(r.get('ADAS配置', '')))}</li>")
    blocks.append("</ul>")

    blocks.append("<h3>品牌分组</h3>")
    blocks.append(
        _html_table(
            brand_rows,
            ["品牌", "车型数", "平均快充时间(分钟)", "平均CLTC续航(km)", "平均电池容量(kWh)"],
        )
    )

    def rank_table(src: list[dict[str, str]], metric: str) -> str:
        mini: list[dict[str, str]] = []
        for r in src:
            mini.append(
                {
                    "车系ID": r.get("车系ID", ""),
                    "品牌": r.get("品牌", ""),
                    "车型": r.get("车型", ""),
                    metric: r.get(metric, ""),
                    "高压快充平台": r.get("高压快充平台", ""),
                    "电池容量(kWh)": r.get("电池容量(kWh)", ""),
                }
            )
        return _html_table(mini, ["车系ID", "品牌", "车型", metric, "高压快充平台", "电池容量(kWh)"])

    blocks.append("<h3>Top/Bottom 对比</h3>")
    blocks.append("<h4>Top 5 最快快充（分钟越小越好）</h4>")
    blocks.append(rank_table(best_fast, "快充时间(分钟)"))
    blocks.append("<h4>Bottom 5 最慢快充（分钟越大越慢）</h4>")
    blocks.append(rank_table(bottom_fast, "快充时间(分钟)"))
    blocks.append("<h4>Top 5 CLTC续航</h4>")
    blocks.append(rank_table(top_range, "纯电续航里程(km)CLTC"))
    blocks.append("<h4>Bottom 5 CLTC续航</h4>")
    blocks.append(rank_table(bottom_range, "纯电续航里程(km)CLTC"))
    blocks.append("<h4>Top 5 电池能量密度</h4>")
    blocks.append(rank_table(top_density, "电池能量密度(Wh/kg)"))

    return "".join(blocks)


def _sort_rows_for_report(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    def sort_key(r: dict[str, str]) -> tuple[Any, ...]:
        platform_v = _to_num(r, "高压平台电压(V)")
        fast_min = _to_num(r, "快充时间(分钟)")
        cltc = _to_num(r, "纯电续航里程(km)CLTC")
        cap = _to_num(r, "电池容量(kWh)")
        price = _to_num(r, "价格(万元)")
        return (
            0 if platform_v is not None else 1,
            -(platform_v or 0),
            0 if fast_min is not None else 1,
            fast_min or 99999,
            0 if cltc is not None else 1,
            -(cltc or 0),
            0 if cap is not None else 1,
            -(cap or 0),
            -(price or 0),
            _clean(r.get("品牌")),
            _clean(r.get("车型")),
        )

    return sorted(rows, key=sort_key)


def _load_dotenv_once() -> None:
    # Use utf-8-sig so .env files saved with BOM still parse the first key correctly.
    load_dotenv(ROOT / ".env", encoding="utf-8-sig")


def _confluence_request_once(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    auth_mode: str,
) -> requests.Response:
    base_url = os.getenv("CONFLUENCE_BASE_URL", "").strip().rstrip("/")
    email = os.getenv("CONFLUENCE_EMAIL", "").strip()
    token = os.getenv("CONFLUENCE_API_TOKEN", "").strip()
    if not base_url or not email or not token:
        raise RuntimeError("Missing Confluence credentials in .env")

    url = f"{base_url}{path}"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    kwargs: dict[str, Any] = {"params": params, "json": json_body, "headers": headers, "timeout": 30}

    if auth_mode == "basic":
        kwargs["auth"] = (email, token)
    elif auth_mode == "bearer":
        headers["Authorization"] = f"Bearer {token}"
    else:
        raise ValueError(f"Unsupported auth mode: {auth_mode}")

    return requests.request(method, url, **kwargs)


def _confluence_request(method: str, path: str, *, params: dict[str, Any] | None = None, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
    auth_type = os.getenv("CONFLUENCE_AUTH_TYPE", "auto").strip().lower()

    if auth_type == "auto":
        first = _confluence_request_once(method, path, params=params, json_body=json_body, auth_mode="bearer")
        if first.status_code in (401, 403):
            response = _confluence_request_once(method, path, params=params, json_body=json_body, auth_mode="basic")
        else:
            response = first
    elif auth_type in {"basic", "bearer"}:
        response = _confluence_request_once(method, path, params=params, json_body=json_body, auth_mode=auth_type)
    else:
        raise RuntimeError("CONFLUENCE_AUTH_TYPE must be auto/basic/bearer")

    if response.status_code >= 400:
        detail = response.text
        try:
            detail = json.dumps(response.json(), ensure_ascii=False)
        except Exception:
            pass
        raise RuntimeError(f"Confluence API error {response.status_code}: {detail}")

    if not response.text.strip():
        return {}
    return response.json()


def _upsert_confluence_section(page_id: str, section_html: str, run_date: str) -> dict[str, str]:
    page = _confluence_request("GET", f"/rest/api/content/{page_id}", params={"expand": "body.storage,version,title"})

    title = _clean(page.get("title"))
    body = _clean(((page.get("body") or {}).get("storage") or {}).get("value"))
    version_raw = ((page.get("version") or {}).get("number"))
    try:
        version = int(version_raw)
    except Exception:
        version = 1

    start_marker = f"<!-- DONGCHEDI_DAILY:{run_date}:START -->"
    end_marker = f"<!-- DONGCHEDI_DAILY:{run_date}:END -->"
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)

    if pattern.search(body):
        updated_body = pattern.sub(section_html, body)
    else:
        updated_body = body + section_html

    payload = {
        "id": page_id,
        "type": "page",
        "title": title,
        "version": {"number": version + 1},
        "body": {"storage": {"value": updated_body, "representation": "storage"}},
    }

    updated = _confluence_request("PUT", f"/rest/api/content/{page_id}", json_body=payload)

    return {
        "status": "ok",
        "page_id": _clean(updated.get("id")) or page_id,
        "title": _clean(updated.get("title")) or title,
        "version": str(((updated.get("version") or {}).get("number")) or version + 1),
    }


def _write_log(log: dict[str, Any]) -> None:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = REPORT_ROOT / "run_log.jsonl"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")


def _collect_existing_report_dates() -> set[str]:
    existing: set[str] = set()
    if not REPORT_ROOT.exists():
        return existing

    for p in REPORT_ROOT.iterdir():
        if not p.is_dir():
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name):
            continue
        if (p / "filtered.json").exists():
            existing.add(p.name)

    return existing


def run(args: argparse.Namespace) -> int:
    # Auto backfill: replay missing historical days only.
    # Today runs only when missing, never rerun if already generated.
    if (
        not getattr(args, "_backfill_dispatch", False)
        and not args.date
        and not args.no_backfill_missing
    ):
        today = dt.date.today()
        today_str = today.isoformat()
        backfill_days = max(0, int(args.backfill_days))
        existing_dates = _collect_existing_report_dates()

        planned_dates: list[str] = []

        # Historical window excludes today: [today-backfill_days, today-1]
        for offset in range(backfill_days, 0, -1):
            d = (today - dt.timedelta(days=offset)).isoformat()
            if d not in existing_dates:
                planned_dates.append(d)

        # Run today only when missing.
        if today_str not in existing_dates:
            planned_dates.append(today_str)

        if planned_dates:
            print("Backfill planned dates: " + ", ".join(planned_dates))
        else:
            print("Backfill planned dates: none (all existing, today already generated)")

        failed: list[str] = []
        for d in planned_dates:
            child = argparse.Namespace(**vars(args))
            child.date = d
            child._backfill_dispatch = True
            try:
                run(child)
            except Exception as exc:
                failed.append(f"{d}: {exc}")
                print(f"Backfill failed for {d}: {exc}")

        if failed:
            raise RuntimeError("Backfill failed for dates: " + " | ".join(failed))
        return 0

    _load_dotenv_once()

    run_date = args.date or dt.date.today().isoformat()
    output_dir = REPORT_ROOT / run_date
    output_dir.mkdir(parents=True, exist_ok=True)

    refresh_log_path = output_dir / "refresh_log.json"
    refresh_failures_path = output_dir / "refresh_failures.json"

    refresh_result: dict[str, Any] | None = None
    if args.refresh_source:
        base_source = _find_latest_source(args.source)
        refreshed_source = ROOT / f"dongchedi_full_configs_{run_date}.csv"
        refresh_result = refresh_source_csv(
            base_source=base_source,
            output_csv=refreshed_source,
            max_series=args.refresh_source_max_series,
            timeout_sec=args.refresh_source_timeout,
            min_successes=args.refresh_source_min_successes,
            min_success_rate=args.refresh_source_min_success_rate,
            strict_mode=args.refresh_source_strict,
        )
        refresh_log_path.write_text(json.dumps(refresh_result, ensure_ascii=False, indent=2), encoding="utf-8")
        refresh_failures = [
            item for item in refresh_result.get("series_results", []) if _clean(item.get("status")) != "ok"
        ]
        refresh_failures_path.write_text(
            json.dumps(
                {
                    "run_date": run_date,
                    "target_series": refresh_result.get("target_series", 0),
                    "refreshed_series": refresh_result.get("refreshed_series", 0),
                    "success_rate": refresh_result.get("success_rate", 0.0),
                    "failed_series": len(refresh_failures),
                    "failures": refresh_failures,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        source_file = refreshed_source
    else:
        source_file = _find_latest_source(args.source)
    source_rows = _load_csv_rows(source_file)

    price_map_path = Path(args.price_map)
    if not price_map_path.is_absolute():
        price_map_path = ROOT / price_map_path

    pair_price_map, series_price_map = _load_price_map(price_map_path)

    if not pair_price_map and not series_price_map:
        if not price_map_path.exists():
            _create_price_map_template(price_map_path, source_rows)
            raise RuntimeError(
                f"Price map is required for price>20万 filtering. Template created at {price_map_path}. Fill 价格(万元) then rerun."
            )

    source_price_cols = [
        c
        for c in ["官方指导价(万元)", "厂商指导价(万元)", "指导价(万元)", "价格(万元)", "价格"]
        if source_rows and c in source_rows[0]
    ]

    if not pair_price_map and not series_price_map and not source_price_cols:
        raise RuntimeError(
            f"No usable price values found. Fill 价格(万元) in {price_map_path} before rerun."
        )

    previous_rows = _load_previous_rows(run_date)
    prev_map = {_model_key(r): r for r in previous_rows}

    today_selected: list[dict[str, str]] = []
    unresolved_price_models: list[str] = []

    for row in source_rows:
        if _clean(row.get("车型")) == "本批合计提取44条配置":
            continue

        power = _clean(row.get("动力形式"))
        if not _infer_powertrain_scope(power, args.powertrain_mode):
            continue

        price_wan = _resolve_price(row, pair_price_map, series_price_map, source_price_cols)
        if price_wan is None:
            unresolved_price_models.append(_model_key(row))
            continue

        if price_wan <= args.price_threshold_wan:
            continue

        out = _to_output_row(row, run_date, price_wan, "当日采集")
        out["缺失状态"] = _missing_status(out)
        today_selected.append(out)

    today_map = {_model_key(r): r for r in today_selected}

    carried_rows: list[dict[str, str]] = []
    for k, prev in prev_map.items():
        if k in today_map:
            continue
        try:
            prev_price = float(_clean(prev.get("价格(万元)")) or 0)
        except ValueError:
            prev_price = 0
        if prev_price <= args.price_threshold_wan:
            continue

        carry = dict(prev)
        carry["数据日期"] = run_date
        carry["数据状态"] = "昨日沿用(当日未出现)"
        carry["缺失状态"] = _missing_status(carry)
        carried_rows.append(carry)

    final_rows = _sort_rows_for_report(today_selected + carried_rows)

    if not final_rows and unresolved_price_models:
        raise RuntimeError(
            f"No rows matched because price values are unresolved. Update {price_map_path} and rerun."
        )

    diff = _build_diff(final_rows, previous_rows)

    filtered_csv = output_dir / "filtered.csv"
    filtered_json = output_dir / "filtered.json"
    summary_md = output_dir / "summary.md"
    confluence_section_path = output_dir / "confluence_section.html"

    _write_csv(filtered_csv, final_rows)
    filtered_json.write_text(json.dumps(final_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        f"# 懂车帝充电日报 {run_date}",
        "",
        f"- 数据源: {source_file.name}",
        f"- 筛选规则: 价格>{args.price_threshold_wan}万 且 动力范围={args.powertrain_mode}",
        f"- 当日总车型: {len(final_rows)}",
        f"- 昨日沿用车型: {sum(1 for r in final_rows if r.get('数据状态') != '当日采集')}",
        f"- 新增车型: {diff['added_count']}",
        f"- 移除车型: {diff['removed_count']}",
        f"- 缺失转完整: {diff['improved_count']}",
        f"- 价格缺失(未纳入筛选): {len(set(unresolved_price_models))}",
        "",
        _build_summary_blocks(final_rows),
        "",
        "## 车型明细",
        "",
        _rows_to_markdown(final_rows),
        "",
    ]

    summary_md.write_text("\n".join(md_lines), encoding="utf-8")

    section_html = _build_daily_section_html(
        run_date=run_date,
        source_file=source_file,
        current_rows=final_rows,
        diff=diff,
        unresolved_price_count=len(set(unresolved_price_models)),
    )
    confluence_section_path.write_text(section_html, encoding="utf-8")

    confluence_result: dict[str, str] | None = None
    if not args.skip_confluence and not args.dry_run:
        page_id = _clean(args.confluence_page_id or os.getenv("CONFLUENCE_DAILY_PAGE_ID", ""))
        if not page_id:
            raise RuntimeError("Missing CONFLUENCE_DAILY_PAGE_ID. Set it in .env or pass --confluence-page-id")
        confluence_result = _upsert_confluence_section(page_id, section_html, run_date)

    log = {
        "ts": dt.datetime.now().isoformat(timespec="seconds"),
        "run_date": run_date,
        "source_file": str(source_file),
        "price_map": str(price_map_path),
        "price_threshold_wan": args.price_threshold_wan,
        "row_count": len(final_rows),
        "added_count": diff["added_count"],
        "removed_count": diff["removed_count"],
        "improved_count": diff["improved_count"],
        "unresolved_price_count": len(set(unresolved_price_models)),
        "dry_run": args.dry_run,
        "skip_confluence": args.skip_confluence,
        "confluence_result": confluence_result,
        "refresh_result": refresh_result,
        "output_dir": str(output_dir),
    }
    _write_log(log)

    print(f"Run date: {run_date}")
    print(f"Source: {source_file}")
    print(f"Output: {output_dir}")
    print(f"Rows: {len(final_rows)}")
    if refresh_result:
        print(
            "Source refresh: "
            f"{refresh_result['refreshed_series']}/{refresh_result['target_series']} series refreshed, "
            f"{refresh_result['failed_series']} failed, "
            f"success_rate={refresh_result.get('success_rate', 0):.2%}"
        )
    if confluence_result:
        print(f"Confluence updated: page {confluence_result['page_id']} v{confluence_result['version']}")
    elif args.dry_run or args.skip_confluence:
        print("Confluence update skipped.")

    if len(set(unresolved_price_models)) > 0:
        print(f"Warning: unresolved price models not included: {len(set(unresolved_price_models))}")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and deliver Dongchedi daily charging report.")
    parser.add_argument("--date", default="", help="Run date in YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--source", default="", help="Source CSV path. Defaults to latest dongchedi_full_configs_*.csv")
    parser.add_argument("--price-map", default=str(PRICE_MAP_DEFAULT), help="Price mapping CSV path.")
    parser.add_argument("--price-threshold-wan", type=float, default=20.0, help="Price threshold in 万元.")
    parser.add_argument(
        "--powertrain-mode",
        choices=["pure_ev", "nev", "all"],
        default="pure_ev",
        help="Filter scope for 动力形式. Defaults to pure_ev to preserve existing behavior.",
    )
    parser.add_argument(
        "--no-backfill-missing",
        action="store_true",
        help="Disable auto backfill for missing days when --date is not provided.",
    )
    parser.add_argument(
        "--backfill-days",
        type=int,
        default=7,
        help="Look back this many days to detect and replay missing report dates.",
    )
    parser.add_argument(
        "--refresh-source",
        action="store_true",
        help="Refresh the latest Dongchedi source CSV from live params pages before generating the report.",
    )
    parser.add_argument(
        "--refresh-source-timeout",
        type=int,
        default=25,
        help="Per-series timeout in seconds for live Dongchedi refresh.",
    )
    parser.add_argument(
        "--refresh-source-max-series",
        type=int,
        default=0,
        help="Limit how many series IDs to refresh. 0 means all series in the base source.",
    )
    parser.add_argument(
        "--refresh-source-min-successes",
        type=int,
        default=1,
        help="Fail refresh when fewer than this many series pages are refreshed successfully.",
    )
    parser.add_argument(
        "--refresh-source-strict",
        action="store_true",
        help="Enable strict mode: fail run when refresh success rate is below threshold.",
    )
    parser.add_argument(
        "--refresh-source-min-success-rate",
        type=float,
        default=0.0,
        help="Minimum refresh success rate in [0,1] used with --refresh-source-strict.",
    )
    parser.add_argument("--confluence-page-id", default="", help="Confluence page ID for daily append.")
    parser.add_argument("--skip-confluence", action="store_true", help="Generate local artifacts only.")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode; always skip Confluence update.")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        raise SystemExit(run(parse_args()))
    except Exception as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)

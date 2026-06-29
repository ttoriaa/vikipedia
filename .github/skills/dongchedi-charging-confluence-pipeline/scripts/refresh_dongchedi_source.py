from __future__ import annotations

import argparse
import csv
import datetime as dt
import glob
import json
import re
import time
from pathlib import Path
from typing import Any

import requests


def _resolve_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "reports").exists() and (parent / "dongchedi_price_map.csv").exists():
            return parent
    return p.parents[1]


ROOT = _resolve_root()
MISSING_VALUE = "未明确显示"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

FIELD_LABEL_ALIASES: dict[str, list[str]] = {
    "动力形式": ["能源类型"],
    "纯电续航里程(km)工信部": ["纯电续航里程(km)工信部"],
    "纯电续航里程(km)CLTC": ["纯电续航里程(km)CLTC"],
    "高压快充平台": ["高压快充平台"],
    "充电时间": ["充电时间"],
    "快充电量(%)": ["快充电量(%)"],
    "电池类型": ["电池类型"],
    "电芯品牌": ["电芯品牌"],
    "电池容量(kWh)": ["电池容量(kWh)"],
    "电池能量密度(Wh/kg)": ["电池能量密度(Wh/kg)"],
    "换电支持": ["换电", "支持换电", "换电支持"],
    "ADAS配置": ["辅助驾驶级别", "智能辅助驾驶", "辅助驾驶", "高阶辅助驾驶", "激光雷达", "城区辅助驾驶"],
    "电控系统": ["电控系统", "电机控制器", "电控"],
    "发电机马力(Ps)": ["发电机总马力(Ps)", "发电机马力(Ps)", "发电机马力"],
    "电动机": ["电动机描述", "电动机"],
    "电机类型": ["电机类型"],
    "电动机总功率": ["电动机总功率(kW)"],
    "电动机总功率(kW)": ["电动机总功率(kW)"],
    "电动机总马力": ["电动机总马力(Ps)"],
    "电动机总马力(Ps)": ["电动机总马力(Ps)"],
    "电动机总扭矩": ["电动机总扭矩(N·m)", "电动机总扭矩(Nm)"],
    "电动机总扭矩(Nm)": ["电动机总扭矩(N·m)", "电动机总扭矩(Nm)"],
    "前电动机最大扭矩": ["前电动机最大扭矩(N·m)", "前电动机最大扭矩(Nm)"],
    "前电动机最大扭矩(Nm)": ["前电动机最大扭矩(N·m)", "前电动机最大扭矩(Nm)"],
    "前电动机最大功率": ["前电动机最大功率(kW)"],
    "前电动机最大功率(kW)": ["前电动机最大功率(kW)"],
    "后电动机最大扭矩": ["后电动机最大扭矩(N·m)", "后电动机最大扭矩(Nm)"],
    "后电动机最大扭矩(Nm)": ["后电动机最大扭矩(N·m)", "后电动机最大扭矩(Nm)"],
    "后电动机最大功率": ["后电动机最大功率(kW)"],
    "后电动机最大功率(kW)": ["后电动机最大功率(kW)"],
    "驱动电机数": ["驱动电机数"],
    "电机布局": ["电机布局"],
}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_missing_like(value: str) -> bool:
    v = _clean(value)
    return (not v) or (v in {MISSING_VALUE, "未完全显示"})


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


def _normalize_model_name(name: str) -> str:
    return re.sub(r"\s+", "", _clean(name))


def _series_ids(rows: list[dict[str, str]], max_series: int) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for row in rows:
        sid = _clean(row.get("车系ID"))
        if not sid or sid in seen:
            continue
        seen.add(sid)
        ids.append(sid)
    if max_series > 0:
        return ids[:max_series]
    return ids


def _extract_next_data(html_text: str) -> dict[str, Any]:
    match = re.search(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', html_text, re.S)
    if not match:
        raise ValueError("__NEXT_DATA__ not found in response")
    return json.loads(match.group(1))


def _value_from_info(info: dict[str, Any], key: str) -> str:
    entry = info.get(key)
    if not isinstance(entry, dict):
        return ""
    value = _clean(entry.get("value"))
    icon_type = entry.get("icon_type")
    if not value and icon_type == 3:
        return MISSING_VALUE
    return value


def _field_key_map(raw_data: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for prop in raw_data.get("properties", []):
        text = _clean(prop.get("text"))
        key = _clean(prop.get("key"))
        if text and key:
            mapping[text] = key
    return mapping


def _compose_model_name(car: dict[str, Any]) -> str:
    brand = _clean(car.get("brand_name"))
    series = _clean(car.get("series_name"))
    car_name = _clean(car.get("car_name"))
    if brand and series and car_name:
        return f"{brand}{series} {car_name}"
    return car_name or f"{brand}{series}" or "未明确显示"


def _base_row_for_car(
    fieldnames: list[str],
    sid: str,
    model_name: str,
    base_lookup: dict[str, dict[str, str]],
) -> dict[str, str]:
    row = dict.fromkeys(fieldnames, MISSING_VALUE)
    existing = base_lookup.get(f"{sid}||{_normalize_model_name(model_name)}")
    if existing:
        row.update(existing)
    row["车系ID"] = sid
    row["车型"] = model_name
    return row


def _populate_row_from_car(
    row: dict[str, str],
    car: dict[str, Any],
    field_key_map: dict[str, str],
) -> dict[str, str]:
    info = car.get("info") or {}
    row["车系ID"] = _clean(car.get("series_id")) or row.get("车系ID", MISSING_VALUE)
    row["车型"] = _compose_model_name(car)

    for dest_field, aliases in FIELD_LABEL_ALIASES.items():
        matched_alias = next((label for label in aliases if label in field_key_map), "")
        if not matched_alias:
            continue
        key = field_key_map[matched_alias]
        value = _value_from_info(info, key)
        if _is_missing_like(value):
            existing = _clean(row.get(dest_field, ""))
            row[dest_field] = existing if not _is_missing_like(existing) else MISSING_VALUE
        else:
            row[dest_field] = value

    return row


def _fetch_series_payload(session: requests.Session, sid: str, timeout_sec: int, retries: int = 2) -> dict[str, Any]:
    url = f"https://www.dongchedi.com/auto/params-carIds-x-{sid}"
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=(timeout_sec, timeout_sec))
            response.raise_for_status()
            return _extract_next_data(response.text)
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(2 * attempt, 4))
    raise RuntimeError(f"Series {sid} refresh failed: {last_error}")


def refresh_source_csv(
    base_source: Path,
    output_csv: Path,
    max_series: int = 0,
    timeout_sec: int = 25,
    min_successes: int = 1,
    min_success_rate: float = 0.0,
    strict_mode: bool = False,
) -> dict[str, Any]:
    with base_source.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        base_rows = list(reader)

    if not fieldnames:
        raise RuntimeError(f"No header found in base source: {base_source}")

    base_lookup = {
        f"{_clean(row.get('车系ID'))}||{_normalize_model_name(row.get('车型', ''))}": row
        for row in base_rows
        if _clean(row.get("车系ID")) and _clean(row.get("车型"))
    }
    target_series = _series_ids(base_rows, max_series=max_series)

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    refreshed_by_sid: dict[str, list[dict[str, str]]] = {}
    failures: list[str] = []
    series_results: list[dict[str, Any]] = []

    for sid in target_series:
        try:
            payload = _fetch_series_payload(session, sid=sid, timeout_sec=timeout_sec)
            raw_data = payload.get("props", {}).get("pageProps", {}).get("rawData", {})
            field_map = _field_key_map(raw_data)
            car_info = raw_data.get("car_info") or []
            series_rows: list[dict[str, str]] = []
            for car in car_info:
                model_name = _compose_model_name(car)
                row = _base_row_for_car(fieldnames, sid=sid, model_name=model_name, base_lookup=base_lookup)
                series_rows.append(_populate_row_from_car(row, car=car, field_key_map=field_map))
            if series_rows:
                refreshed_by_sid[sid] = series_rows
                series_results.append(
                    {
                        "series_id": sid,
                        "status": "ok",
                        "row_count": len(series_rows),
                        "error": "",
                    }
                )
            else:
                message = "no car rows found"
                failures.append(f"{sid}: {message}")
                series_results.append(
                    {
                        "series_id": sid,
                        "status": "failed",
                        "row_count": 0,
                        "error": message,
                    }
                )
        except Exception as exc:
            message = str(exc)
            failures.append(f"{sid}: {message}")
            series_results.append(
                {
                    "series_id": sid,
                    "status": "failed",
                    "row_count": 0,
                    "error": message,
                }
            )

    refreshed_count = len(refreshed_by_sid)
    target_count = len(target_series)
    success_rate = (refreshed_count / target_count) if target_count > 0 else 1.0

    if strict_mode and target_count > 0 and success_rate < min_success_rate:
        raise RuntimeError(
            "Dongchedi source refresh aborted by strict mode: "
            f"success rate {success_rate:.3f} below threshold {min_success_rate:.3f}. "
            f"Refreshed {refreshed_count}/{target_count}. "
            f"Failures: {' | '.join(failures[:5])}"
        )

    if refreshed_count < min_successes:
        raise RuntimeError(
            f"Dongchedi source refresh aborted: refreshed {refreshed_count}/{target_count} series, "
            f"required at least {min_successes}. Failures: {' | '.join(failures[:5])}"
        )

    ordered_series: list[str] = []
    grouped_base: dict[str, list[dict[str, str]]] = {}
    for row in base_rows:
        sid = _clean(row.get("车系ID"))
        if sid not in grouped_base:
            grouped_base[sid] = []
            ordered_series.append(sid)
        grouped_base[sid].append(row)

    merged_rows: list[dict[str, str]] = []
    for sid in ordered_series:
        if sid in refreshed_by_sid:
            merged_rows.extend(refreshed_by_sid[sid])
        else:
            merged_rows.extend(grouped_base.get(sid, []))

    for sid, rows in refreshed_by_sid.items():
        if sid not in grouped_base:
            merged_rows.extend(rows)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged_rows)

    return {
        "base_source": str(base_source),
        "output_csv": str(output_csv),
        "target_series": target_count,
        "refreshed_series": refreshed_count,
        "success_rate": round(success_rate, 6),
        "strict_mode": strict_mode,
        "min_success_rate": min_success_rate,
        "failed_series": len(failures),
        "failures": failures,
        "series_results": series_results,
        "row_count": len(merged_rows),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh Dongchedi source CSV from live params pages.")
    parser.add_argument("--source", default="", help="Base source CSV path. Defaults to latest dongchedi_full_configs_*.csv")
    parser.add_argument("--output", default="", help="Output CSV path. Defaults to dongchedi_full_configs_YYYY-MM-DD.csv")
    parser.add_argument("--date", default="", help="Date suffix for default output name. Defaults to today.")
    parser.add_argument("--max-series", type=int, default=0, help="Limit how many series IDs to refresh. 0 means all.")
    parser.add_argument("--timeout", type=int, default=25, help="Per-series request timeout in seconds.")
    parser.add_argument("--min-successes", type=int, default=1, help="Fail if fewer than this many series refreshes succeed.")
    parser.add_argument(
        "--strict-mode",
        action="store_true",
        help="Enable strict mode. Refresh fails when success rate is below --min-success-rate.",
    )
    parser.add_argument(
        "--min-success-rate",
        type=float,
        default=0.0,
        help="Minimum acceptable refresh success rate in [0,1] for strict mode.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_date = args.date or dt.date.today().isoformat()
    base_source = _find_latest_source(args.source)
    output_csv = Path(args.output) if args.output else ROOT / f"dongchedi_full_configs_{run_date}.csv"
    if not output_csv.is_absolute():
        output_csv = ROOT / output_csv

    result = refresh_source_csv(
        base_source=base_source,
        output_csv=output_csv,
        max_series=args.max_series,
        timeout_sec=args.timeout,
        min_successes=args.min_successes,
        min_success_rate=max(0.0, min(1.0, args.min_success_rate)),
        strict_mode=args.strict_mode,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

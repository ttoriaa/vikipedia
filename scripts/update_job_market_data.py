#!/usr/bin/env python3
"""Update job_market_hub data with incremental library + daily snapshots."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import glob
import hashlib
import json
import os
import re
import shutil
import sys
import time
from html import unescape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

TARGET_ROLES = ["车辆项目管理", "数据产品经理", "数据项目管理", "技术售前支持"]

CITY_CODE_DEFAULT = ["101010100", "101020100", "101280100", "101210100", "101190400"]

ROLE_KEYWORDS = {
    "车辆项目管理": ["车辆项目", "整车项目", "项目经理", "项目管理", "vehicle project"],
    "数据产品经理": ["数据产品", "data product", "产品经理", "数据平台产品"],
    "数据项目管理": ["数据项目", "项目管理", "data project", "数据交付"],
    "技术售前支持": ["售前", "技术支持", "presales", "solution architect", "方案顾问"],
}

INDUSTRY_KEYWORDS = {
    "机器人与具身智能": ["机器人", "具身", "embodied", "robot", "机械臂", "智能体"],
    "车企": ["汽车", "车企", "整车", "动力总成", "autonomous driving", "smart cockpit", "主机厂"],
    "互联网": ["互联网", "平台", "云", "saas", "ai", "数据中台", "增长"],
}

ROLE_REQUIREMENTS = {
    "车辆项目管理": ["cross-functional", "project delivery", "requirements", "data pipeline"],
    "数据产品经理": ["data governance", "analytics", "requirements", "ai agent"],
    "数据项目管理": ["project delivery", "data governance", "cross-functional", "analytics"],
    "技术售前支持": ["client communication", "requirements", "project delivery", "analytics"],
}

QUERY_TERMS = [
    "车辆项目管理",
    "数据产品经理",
    "数据项目管理",
    "技术售前支持",
    "机器人 数据产品",
    "具身智能 项目经理",
]

DEFAULT_OUT = Path("job_market_hub/data/jobs.json")
DEFAULT_HISTORY_ROOT = Path("job_market_hub/data/history")
DEFAULT_SNAPSHOT_INDEX = Path("job_market_hub/data/snapshots_index.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update job market data for job_market_hub")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON library path")
    parser.add_argument("--max-pages", type=int, default=2, help="Max pages for each BOSS query")
    parser.add_argument(
        "--city-codes",
        default=",".join(CITY_CODE_DEFAULT),
        help="Comma-separated city codes for BOSS query",
    )
    parser.add_argument(
        "--csv-glob",
        default="job_market_hub/data/raw/*.csv",
        help="Glob pattern for local CSV sources",
    )
    parser.add_argument("--skip-boss", action="store_true", help="Skip BOSS scraping and only load local CSV")
    parser.add_argument("--min-delay", type=float, default=0.8, help="Minimum delay between BOSS requests")
    parser.add_argument(
        "--mode",
        choices=["incremental", "replace"],
        default="incremental",
        help="incremental keeps existing library and updates changed jobs; replace overwrites library with today's jobs",
    )
    parser.add_argument(
        "--history-root",
        default=str(DEFAULT_HISTORY_ROOT),
        help="Root folder for per-date snapshots",
    )
    parser.add_argument(
        "--snapshot-index",
        default=str(DEFAULT_SNAPSHOT_INDEX),
        help="Snapshot index JSON path for date-based review",
    )
    parser.add_argument(
        "--snapshot-date",
        default="",
        help="Snapshot date in YYYY-MM-DD, defaults to today (UTC)",
    )
    parser.add_argument(
        "--keep-days",
        type=int,
        default=120,
        help="Keep latest N days in history/index, <=0 means keep all",
    )
    return parser.parse_args()


def normalize_text(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def infer_role(title: str, description: str) -> str:
    content = f"{title} {description}".lower()
    for role, terms in ROLE_KEYWORDS.items():
        for term in terms:
            if term.lower() in content:
                return role
    return "数据项目管理"


def infer_industry(title: str, company: str, description: str) -> str:
    content = f"{title} {company} {description}".lower()
    for industry, terms in INDUSTRY_KEYWORDS.items():
        if any(term.lower() in content for term in terms):
            return industry
    return "互联网"


def make_job_id(item: dict[str, Any]) -> str:
    seed = "|".join([item.get("title", ""), item.get("company", ""), item.get("city", ""), item.get("source", "")])
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
    return f"JOB-{digest.upper()}"


def ensure_job_shape(raw: dict[str, Any]) -> dict[str, Any] | None:
    title = normalize_text(str(raw.get("title", "")))
    company = normalize_text(str(raw.get("company", "")))
    if not title or not company:
        return None

    description = normalize_text(str(raw.get("description", "")))
    role = normalize_text(str(raw.get("role", ""))) or infer_role(title, description)
    if role not in TARGET_ROLES:
        role = infer_role(title, description)

    industry = normalize_text(str(raw.get("industry", ""))) or infer_industry(title, company, description)
    city = normalize_text(str(raw.get("city", ""))) or "城市待补充"
    salary = normalize_text(str(raw.get("salary", ""))) or "薪资待补充"
    source = normalize_text(str(raw.get("source", ""))) or "https://www.zhipin.com/web/geek/jobs"

    job = {
        "title": title,
        "company": company,
        "industry": industry,
        "role": role,
        "city": city,
        "salary": salary,
        "description": description or "岗位描述待补充",
        "requirements": ROLE_REQUIREMENTS.get(role, ROLE_REQUIREMENTS["数据项目管理"]),
        "source": source,
    }
    job["id"] = make_job_id(job)
    return job


def extract_json_like_jobs(html: str) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    pattern = re.compile(
        r'"jobName":"(?P<title>.*?)".*?"brandName":"(?P<company>.*?)".*?'
        r'"salaryDesc":"(?P<salary>.*?)".*?"cityName":"(?P<city>.*?)".*?'
        r'"jobUrl":"(?P<url>.*?)"',
        flags=re.DOTALL,
    )

    for match in pattern.finditer(html):
        title = normalize_text(match.group("title").replace("\\/", "/"))
        company = normalize_text(match.group("company").replace("\\/", "/"))
        salary = normalize_text(match.group("salary").replace("\\/", "/"))
        city = normalize_text(match.group("city").replace("\\/", "/"))
        url = normalize_text(match.group("url").replace("\\/", "/"))

        jobs.append(
            {
                "title": title,
                "company": company,
                "salary": salary,
                "city": city,
                "description": "",
                "source": f"https://www.zhipin.com{url}" if url.startswith("/") else url,
            }
        )

    return jobs


def fetch_url(url: str, timeout: int = 25) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    cookie = os.getenv("BOSS_COOKIE", "").strip()
    if cookie:
        headers["Cookie"] = cookie

    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def scrape_boss(max_pages: int, city_codes: list[str], min_delay: float) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []

    for query in QUERY_TERMS:
        encoded_query = quote_plus(query)
        for city in city_codes:
            for page in range(1, max_pages + 1):
                url = f"https://www.zhipin.com/web/geek/jobs?query={encoded_query}&city={city}&page={page}"
                try:
                    html = fetch_url(url)
                    parsed = extract_json_like_jobs(html)
                    records.extend(parsed)
                except HTTPError as exc:
                    errors.append(f"HTTP {exc.code} | {url}")
                except URLError as exc:
                    errors.append(f"URL error {exc.reason} | {url}")
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"Unexpected {exc} | {url}")
                time.sleep(max(min_delay, 0.1))

    return records, errors


def map_csv_row(row: dict[str, str]) -> dict[str, Any]:
    key_map = {
        "title": ["title", "职位", "岗位", "job_title"],
        "company": ["company", "公司", "企业", "company_name"],
        "city": ["city", "城市", "工作城市", "location"],
        "salary": ["salary", "薪资", "薪酬"],
        "description": ["description", "岗位描述", "职责", "jd"],
        "source": ["source", "link", "url", "来源链接"],
        "role": ["role", "岗位类别"],
        "industry": ["industry", "行业"],
    }

    output: dict[str, Any] = {}
    for target_key, aliases in key_map.items():
        for alias in aliases:
            if alias in row and row[alias]:
                output[target_key] = row[alias]
                break
    return output


def load_csv_sources(csv_glob: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for file_path in glob.glob(csv_glob):
        try:
            with open(file_path, "r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    mapped = map_csv_row(row)
                    if mapped:
                        rows.append(mapped)
        except FileNotFoundError:
            continue
    return rows


def merge_two_jobs(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key in ["title", "company", "industry", "role", "city", "salary", "description", "requirements", "source"]:
        incoming_value = incoming.get(key)
        if incoming_value in (None, ""):
            continue
        if key == "description" and incoming_value == "岗位描述待补充":
            continue
        if key == "salary" and incoming_value == "薪资待补充":
            continue
        if key == "city" and incoming_value == "城市待补充":
            continue
        merged[key] = incoming_value
    return merged


def dedupe_jobs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bucket: dict[str, dict[str, Any]] = {}
    for item in items:
        key = item["id"]
        if key not in bucket:
            bucket[key] = item
            continue
        bucket[key] = merge_two_jobs(bucket[key], item)

    return list(bucket.values())


def load_json_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def load_existing_jobs(out_path: Path) -> list[dict[str, Any]]:
    payload = load_json_file(out_path)
    if not payload:
        return []
    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        return []
    return [item for item in jobs if isinstance(item, dict) and "id" in item]


def merge_incremental(existing_jobs: list[dict[str, Any]], incoming_jobs: list[dict[str, Any]], snapshot_date: str) -> list[dict[str, Any]]:
    existing_map = {item["id"]: dict(item) for item in existing_jobs}

    for item in existing_map.values():
        item.setdefault("first_seen", snapshot_date)
        item.setdefault("last_seen", item.get("first_seen", snapshot_date))

    for item in incoming_jobs:
        key = item["id"]
        if key in existing_map:
            merged = merge_two_jobs(existing_map[key], item)
            merged["first_seen"] = existing_map[key].get("first_seen", snapshot_date)
            merged["last_seen"] = snapshot_date
            existing_map[key] = merged
        else:
            new_item = dict(item)
            new_item["first_seen"] = snapshot_date
            new_item["last_seen"] = snapshot_date
            existing_map[key] = new_item

    merged_jobs = list(existing_map.values())
    merged_jobs.sort(key=lambda item: (item.get("industry", ""), item.get("role", ""), item.get("title", "")))
    return merged_jobs


def build_payload(
    jobs: list[dict[str, Any]],
    sources: list[str],
    errors: list[str],
    snapshot_date: str,
    mode: str,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "meta": {
            "generated_at": generated_at,
            "snapshot_date": snapshot_date,
            "sources": sources,
            "total": len(jobs),
            "mode": mode,
            "errors": errors[:20],
        },
        "jobs": jobs,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_daily_snapshot(history_root: Path, snapshot_date: str, payload: dict[str, Any]) -> Path:
    day_dir = history_root / snapshot_date
    day_dir.mkdir(parents=True, exist_ok=True)
    snapshot_file = day_dir / "jobs.json"
    write_json(snapshot_file, payload)
    return snapshot_file


def to_posix(path: Path) -> str:
    return path.as_posix()


def to_web_path(path: Path) -> str:
    raw = to_posix(path)
    if raw.startswith("job_market_hub/"):
        return raw[len("job_market_hub/") :]
    return raw


def update_snapshot_index(
    index_path: Path,
    snapshot_date: str,
    snapshot_file: Path,
    payload: dict[str, Any],
    keep_days: int,
) -> None:
    existing = load_json_file(index_path) or {}
    records = existing.get("snapshots") if isinstance(existing.get("snapshots"), list) else []

    file_value = to_web_path(snapshot_file)
    new_record = {
        "date": snapshot_date,
        "file": file_value,
        "total": payload.get("meta", {}).get("total", 0),
        "generated_at": payload.get("meta", {}).get("generated_at", ""),
        "sources": payload.get("meta", {}).get("sources", []),
    }

    record_map: dict[str, dict[str, Any]] = {}
    for row in records:
        if isinstance(row, dict) and isinstance(row.get("date"), str):
            record_map[row["date"]] = row
    record_map[snapshot_date] = new_record

    snapshot_rows = sorted(record_map.values(), key=lambda item: item["date"], reverse=True)

    if keep_days > 0:
        snapshot_rows = snapshot_rows[:keep_days]

    kept_dates = {row["date"] for row in snapshot_rows}
    history_root = snapshot_file.parent.parent
    if keep_days > 0 and history_root.exists():
        for child in history_root.iterdir():
            if child.is_dir() and child.name not in kept_dates:
                shutil.rmtree(child, ignore_errors=True)

    out_payload = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "total_snapshots": len(snapshot_rows),
        "snapshots": snapshot_rows,
    }
    write_json(index_path, out_payload)


def resolve_snapshot_date(raw: str) -> str:
    if raw:
        return raw
    return dt.datetime.now(dt.UTC).date().isoformat()


def main() -> int:
    args = parse_args()

    out_path = Path(args.out)
    history_root = Path(args.history_root)
    snapshot_index_path = Path(args.snapshot_index)
    snapshot_date = resolve_snapshot_date(args.snapshot_date)
    generated_at = dt.datetime.now(dt.UTC).isoformat()

    city_codes = [part.strip() for part in args.city_codes.split(",") if part.strip()]

    collected: list[dict[str, Any]] = []
    sources: list[str] = []
    errors: list[str] = []

    if not args.skip_boss:
        boss_raw, boss_errors = scrape_boss(args.max_pages, city_codes, args.min_delay)
        for row in boss_raw:
            shaped = ensure_job_shape(row)
            if shaped:
                collected.append(shaped)
        if boss_raw:
            sources.append("BOSS")
        errors.extend(boss_errors)

    csv_rows = load_csv_sources(args.csv_glob)
    for row in csv_rows:
        shaped = ensure_job_shape(row)
        if shaped:
            collected.append(shaped)
    if csv_rows:
        sources.append("CSV")

    incoming_unique = dedupe_jobs(collected)
    incoming_unique.sort(key=lambda item: (item.get("industry", ""), item.get("role", ""), item.get("title", "")))

    if not incoming_unique and out_path.exists():
        print(f"No new records collected. Keep existing library: {out_path}")
        return 0

    if args.mode == "incremental":
        existing_jobs = load_existing_jobs(out_path)
        library_jobs = merge_incremental(existing_jobs, incoming_unique, snapshot_date)
    else:
        library_jobs = []
        for item in incoming_unique:
            with_seen = dict(item)
            with_seen["first_seen"] = snapshot_date
            with_seen["last_seen"] = snapshot_date
            library_jobs.append(with_seen)

    if not library_jobs:
        payload_empty = build_payload(
            jobs=[],
            sources=sources or ["none"],
            errors=errors + ["No records collected from any source."],
            snapshot_date=snapshot_date,
            mode=args.mode,
            generated_at=generated_at,
        )
        write_json(out_path, payload_empty)
        snapshot_file = write_daily_snapshot(history_root, snapshot_date, payload_empty)
        update_snapshot_index(snapshot_index_path, snapshot_date, snapshot_file, payload_empty, args.keep_days)
        print(f"Wrote empty snapshot for {snapshot_date}")
        return 0

    library_payload = build_payload(
        jobs=library_jobs,
        sources=sources or ["unknown"],
        errors=errors,
        snapshot_date=snapshot_date,
        mode=args.mode,
        generated_at=generated_at,
    )
    write_json(out_path, library_payload)

    daily_payload = build_payload(
        jobs=incoming_unique,
        sources=sources or ["unknown"],
        errors=errors,
        snapshot_date=snapshot_date,
        mode=args.mode,
        generated_at=generated_at,
    )
    snapshot_file = write_daily_snapshot(history_root, snapshot_date, daily_payload)
    update_snapshot_index(snapshot_index_path, snapshot_date, snapshot_file, daily_payload, args.keep_days)

    print(
        "Updated library {lib_total} jobs, daily snapshot {day_total} jobs at {snapshot_file}".format(
            lib_total=len(library_jobs),
            day_total=len(incoming_unique),
            snapshot_file=snapshot_file,
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

import run_dongchedi_daily as daily


def _resolve_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "reports").exists() and (parent / "dongchedi_price_map.csv").exists():
            return parent
    return p.parents[1]


ROOT = _resolve_root()


def _normalize_date(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return dt.date.today().isoformat()
    if len(raw) == 9 and raw[4] == "-" and raw[5:].isdigit():
        raw = f"{raw[:4]}-{raw[5:7]}-{raw[7:9]}"
    return dt.datetime.strptime(raw, "%Y-%m-%d").date().isoformat()


def _check_keys(keys: list[str]) -> tuple[list[str], dict[str, str]]:
    missing: list[str] = []
    found: dict[str, str] = {}
    for key in keys:
        value = os.getenv(key, "").strip()
        if not value:
            missing.append(key)
        else:
            found[key] = value
    return missing, found


def _result(status: str, payload: dict[str, Any]) -> int:
    print(json.dumps({"status": status, **payload}, ensure_ascii=False, indent=2))
    return 0 if status == "ok" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified precheck for Dongchedi daily run and Confluence publish.")
    parser.add_argument("--date", default="", help="Target run date in YYYY-MM-DD. Also accepts YYYY-MMDD.")
    parser.add_argument("--source", default="", help="Optional source CSV path override (same as run_dongchedi_daily.py).")
    parser.add_argument("--price-map", default=str(daily.PRICE_MAP_DEFAULT), help="Price map CSV path.")
    parser.add_argument(
        "--mode",
        choices=["run-daily", "push-only", "pipeline"],
        default="pipeline",
        help="run-daily checks run_dongchedi_daily publish path; push-only checks push_dongchedi_to_confluence; pipeline checks both.",
    )
    parser.add_argument("--json", action="store_true", help="Reserved for compatibility; output is always JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        run_date = _normalize_date(args.date)
    except ValueError as exc:
        return _result(
            "failed",
            {
                "reason": "invalid_date",
                "input_date": args.date,
                "message": str(exc),
                "next_action": "Use --date in YYYY-MM-DD format.",
            },
        )

    # Keep behavior aligned with existing scripts that load from .env.
    daily._load_dotenv_once()

    source_path: Path | None = None
    source_error = ""
    try:
        source_path = daily._find_latest_source(args.source)
    except Exception as exc:
        source_error = str(exc)

    price_map_path = Path(args.price_map)
    if not price_map_path.is_absolute():
        price_map_path = ROOT / price_map_path

    checks: dict[str, Any] = {
        "resolved_date": run_date,
        "mode": args.mode,
        "env_source": str(ROOT / ".env"),
        "source_csv": str(source_path) if source_path else "",
        "source_check": "pass" if source_path else "fail",
        "price_map": str(price_map_path),
        "price_map_check": "pass" if price_map_path.exists() else "fail",
    }

    errors: list[str] = []
    next_actions: list[str] = []

    if source_error:
        errors.append(source_error)
        next_actions.append("Provide --source or place dongchedi_full_configs_YYYY-MM-DD.csv at workspace root.")

    if not price_map_path.exists():
        errors.append(f"Price map not found: {price_map_path}")
        next_actions.append("Create dongchedi_price_map.csv or pass --price-map with a valid file.")

    if args.mode in {"run-daily", "pipeline"}:
        run_required = [
            "CONFLUENCE_BASE_URL",
            "CONFLUENCE_EMAIL",
            "CONFLUENCE_API_TOKEN",
            "CONFLUENCE_DAILY_PAGE_ID",
        ]
        missing_run, found_run = _check_keys(run_required)
        checks["run_daily_required_keys"] = run_required
        checks["run_daily_found_keys"] = sorted(found_run.keys())
        if missing_run:
            errors.append("run_dongchedi_daily publish requirements missing: " + ", ".join(missing_run))
            next_actions.append("Set missing CONFLUENCE_* variables in .env for run_dongchedi_daily publish path.")

    if args.mode in {"push-only", "pipeline"}:
        push_base_required = [
            "CONFLUENCE_BASE_URL",
            "CONFLUENCE_EMAIL",
            "CONFLUENCE_API_TOKEN",
        ]
        missing_push_base, found_push_base = _check_keys(push_base_required)
        daily_parent = os.getenv("CONFLUENCE_DAILY_PARENT_PAGE_ID", "").strip()
        daily_page = os.getenv("CONFLUENCE_DAILY_PAGE_ID", "").strip()
        checks["push_required_base_keys"] = push_base_required
        checks["push_found_base_keys"] = sorted(found_push_base.keys())
        checks["push_page_id_check"] = "pass" if (daily_parent or daily_page) else "fail"
        if missing_push_base:
            errors.append("push_dongchedi_to_confluence requirements missing: " + ", ".join(missing_push_base))
            next_actions.append("Set missing CONFLUENCE_* variables in .env for push_dongchedi_to_confluence.")
        if not (daily_parent or daily_page):
            errors.append("push_dongchedi_to_confluence requires CONFLUENCE_DAILY_PARENT_PAGE_ID or CONFLUENCE_DAILY_PAGE_ID")
            next_actions.append("Set CONFLUENCE_DAILY_PARENT_PAGE_ID (preferred) or CONFLUENCE_DAILY_PAGE_ID in .env.")

    if errors:
        return _result(
            "failed",
            {
                **checks,
                "errors": errors,
                "next_action": next_actions,
            },
        )

    return _result(
        "ok",
        {
            **checks,
            "next_action": [
                "Safe to run .\\.venv\\Scripts\\python.exe .\\scripts\\run_dongchedi_daily.py --no-backfill-missing --date <resolved_date>",
                "Optional publish step: .\\.venv\\Scripts\\python.exe .\\scripts\\push_dongchedi_to_confluence.py",
            ],
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())

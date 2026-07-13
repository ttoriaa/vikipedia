from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date as date_cls
from pathlib import Path
from typing import Dict
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


LIVE_URLS = {
    "data": "https://ttoriaa.github.io/automotive-benchmarking/data.html",
    "dashboard": "https://ttoriaa.github.io/automotive-benchmarking/dashboard.html",
    "insights": "https://ttoriaa.github.io/automotive-benchmarking/insights.html",
}


def _to_bool(text: str) -> bool:
    v = (text or "").strip().lower()
    if v in {"1", "true", "yes", "y"}:
        return True
    if v in {"0", "false", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {text}")


def _read_text(url: str, timeout: int = 30) -> str:
    req = Request(url, headers={"User-Agent": "ev-benchmark-watchdog/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _check_live(date_text: str) -> Dict[str, Dict[str, object]]:
    out: Dict[str, Dict[str, object]] = {}
    for name, url in LIVE_URLS.items():
        try:
            text = _read_text(url)
            out[name] = {
                "url": url,
                "ok": True,
                "hit_date": date_text in text,
                "length": len(text),
                "error": "",
            }
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            out[name] = {
                "url": url,
                "ok": False,
                "hit_date": False,
                "length": 0,
                "error": str(exc),
            }
    return out


def _all_hit(live_check: Dict[str, Dict[str, object]]) -> bool:
    return all(v.get("ok") and v.get("hit_date") for v in live_check.values())


def parse_args() -> argparse.Namespace:
    this_file = Path(__file__).resolve()
    repo_root = this_file.parents[4]
    default_publisher = repo_root / ".github" / "skills" / "ev-benchmark-daily-publisher" / "scripts" / "publish_ev_benchmark_daily.py"

    parser = argparse.ArgumentParser(description="Watch EV benchmark deployment status and optionally auto-remediate.")
    parser.add_argument("--date", default=date_cls.today().isoformat(), help="Target date in YYYY-MM-DD")
    parser.add_argument("--auto-remediate", default="false", type=_to_bool, help="Whether to auto-run publisher when date is not live")
    parser.add_argument("--max-remediation-attempts", type=int, default=2, help="Maximum remediation attempts")
    parser.add_argument("--publisher-script", default=str(default_publisher), help="Path to publisher script")
    parser.add_argument("--max-wait-seconds", type=int, default=900, help="Pass-through max wait for publisher live checks")
    parser.add_argument("--poll-interval-seconds", type=int, default=20, help="Pass-through poll interval for publisher live checks")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    date_text = args.date

    result: Dict[str, object] = {
        "date": date_text,
        "initial_check": {},
        "attempts": 0,
        "remediation_runs": [],
        "final_check": {},
        "final_status": "failed",
        "next_action": "",
    }

    initial = _check_live(date_text)
    result["initial_check"] = initial
    if _all_hit(initial):
        result["final_check"] = initial
        result["final_status"] = "success"
        result["next_action"] = ""
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not args.auto_remediate:
        result["final_check"] = initial
        result["final_status"] = "failed"
        result["next_action"] = "Date not live. Re-run with --auto-remediate true or run publisher manually."
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    publisher = Path(args.publisher_script).resolve()
    if not publisher.exists():
        result["final_check"] = initial
        result["final_status"] = "failed"
        result["next_action"] = f"Publisher script not found: {publisher}"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3

    for i in range(1, max(1, args.max_remediation_attempts) + 1):
        result["attempts"] = i
        cmd = [
            sys.executable,
            str(publisher),
            "--date",
            date_text,
            "--verify-live",
            "true",
            "--max-wait-seconds",
            str(args.max_wait_seconds),
            "--poll-interval-seconds",
            str(args.poll_interval_seconds),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        run_record = {
            "attempt": i,
            "exit_code": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-3000:],
            "stderr_tail": (proc.stderr or "")[-2000:],
        }
        result["remediation_runs"].append(run_record)

        latest = _check_live(date_text)
        result["final_check"] = latest
        if _all_hit(latest):
            result["final_status"] = "success"
            result["next_action"] = ""
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

    result["final_status"] = "failed"
    result["next_action"] = "Remediation attempts exhausted. Check target repo Actions and publish logs."
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 4


if __name__ == "__main__":
    sys.exit(main())

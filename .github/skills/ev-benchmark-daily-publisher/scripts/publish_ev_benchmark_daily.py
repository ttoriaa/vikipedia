from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import date as date_cls
from pathlib import Path
from typing import Dict, List
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


def _run(cmd: List[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)


def _read_text(url: str, timeout: int = 30) -> str:
    req = Request(url, headers={"User-Agent": "ev-benchmark-publisher/1.0"})
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


def _all_unreachable(live_check: Dict[str, Dict[str, object]]) -> bool:
    return all(not v.get("ok") for v in live_check.values())


def parse_args() -> argparse.Namespace:
    this_file = Path(__file__).resolve()
    repo_root = this_file.parents[4]
    default_target = repo_root.parent / "automotive-benchmarking"

    parser = argparse.ArgumentParser(description="Publish EV benchmark daily artifacts to automotive-benchmarking.")
    parser.add_argument("--date", default=date_cls.today().isoformat(), help="Target date in YYYY-MM-DD")
    parser.add_argument("--source-repo", default=str(repo_root), help="Source repository root path")
    parser.add_argument("--target-repo", default=str(default_target), help="Target repository root path")
    parser.add_argument("--verify-live", default="true", type=_to_bool, help="Whether to verify live pages after push")
    parser.add_argument("--max-wait-seconds", type=int, default=900, help="Max wait time for live verification")
    parser.add_argument("--poll-interval-seconds", type=int, default=20, help="Poll interval for live verification")
    parser.add_argument("--branch", default="main", help="Target git branch")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    date_text = args.date
    source_repo = Path(args.source_repo).resolve()
    target_repo = Path(args.target_repo).resolve()

    source_dir = source_repo / "reports" / "dongchedi_daily" / date_text
    target_dir = target_repo / "reports" / "dongchedi_daily" / date_text

    result: Dict[str, object] = {
        "date": date_text,
        "source_repo": str(source_repo),
        "target_repo": str(target_repo),
        "copied_files": 0,
        "commit_created": False,
        "commit_sha": "",
        "push_status": "skipped",
        "live_check": {},
        "verification_status": "skipped",
        "final_status": "failed",
        "next_action": "",
    }

    required = ["filtered.csv", "filtered.json", "summary.md"]

    if not source_dir.exists():
        result["next_action"] = f"Missing source folder: {source_dir}"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    missing = [x for x in required if not (source_dir / x).exists()]
    if missing:
        result["next_action"] = f"Missing required files in source: {', '.join(missing)}"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    target_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for item in source_dir.iterdir():
        if item.is_file() and item.suffix.lower() in {".csv", ".json", ".md", ".html"}:
            shutil.copy2(item, target_dir / item.name)
            copied += 1
    result["copied_files"] = copied

    add_proc = _run(["git", "add", "--", f"reports/dongchedi_daily/{date_text}"], cwd=target_repo)
    if add_proc.returncode != 0:
        result["next_action"] = add_proc.stderr.strip() or add_proc.stdout.strip() or "git add failed"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3

    staged_proc = _run(["git", "diff", "--cached", "--name-only"], cwd=target_repo)
    staged_files = [x.strip() for x in staged_proc.stdout.splitlines() if x.strip()]
    if not staged_files:
        result["push_status"] = "skipped"
    else:
        msg = f"chore(dongchedi): add {date_text} daily artifacts"
        commit_proc = _run(["git", "commit", "-m", msg], cwd=target_repo)
        if commit_proc.returncode != 0:
            result["next_action"] = commit_proc.stderr.strip() or commit_proc.stdout.strip() or "git commit failed"
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 4
        sha_proc = _run(["git", "rev-parse", "--short", "HEAD"], cwd=target_repo)
        result["commit_created"] = True
        result["commit_sha"] = sha_proc.stdout.strip()

        push_proc = _run(["git", "push", "origin", args.branch], cwd=target_repo)
        if push_proc.returncode != 0:
            result["push_status"] = "failed"
            result["next_action"] = push_proc.stderr.strip() or push_proc.stdout.strip() or "git push failed"
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 5
        result["push_status"] = "success"

    if args.verify_live:
        started = time.time()
        latest_check: Dict[str, Dict[str, object]] = {}
        while True:
            latest_check = _check_live(date_text)
            if _all_hit(latest_check):
                result["live_check"] = latest_check
                result["verification_status"] = "ok"
                result["final_status"] = "success"
                result["next_action"] = ""
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0
            if time.time() - started >= args.max_wait_seconds:
                result["live_check"] = latest_check
                if result["push_status"] == "success" and _all_unreachable(latest_check):
                    result["verification_status"] = "unreachable"
                    result["final_status"] = "push_success_verification_unreachable"
                    result["next_action"] = "Push succeeded, but live verification endpoints were unreachable from this machine. Recheck later or use watchdog scheduled run."
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    return 0
                result["verification_status"] = "timeout"
                result["final_status"] = "failed"
                result["next_action"] = "Push completed but live pages not updated before timeout. Check GitHub Actions runs."
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 6
            time.sleep(max(1, args.poll_interval_seconds))

    result["final_status"] = "success"
    result["verification_status"] = "skipped"
    result["next_action"] = ""
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

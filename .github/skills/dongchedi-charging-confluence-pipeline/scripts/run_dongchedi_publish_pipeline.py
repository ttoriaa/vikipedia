from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _resolve_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "reports").exists() and (parent / "dongchedi_price_map.csv").exists():
            return parent
    return current.parents[1]


ROOT = _resolve_root()
SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_EXE = ROOT / ".venv" / "Scripts" / "python.exe"
RUN_DAILY = SCRIPT_DIR / "run_dongchedi_daily.py"
PUSH_CONFLUENCE = SCRIPT_DIR / "push_dongchedi_to_confluence.py"
PUSH_FEISHU = SCRIPT_DIR / "push_dongchedi_to_feishu.py"


def _run_command(args: list[str]) -> None:
    result = subprocess.run(args, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(args)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Dongchedi daily artifacts and optionally publish to Confluence or Feishu.")
    parser.add_argument("--date", default="", help="Run date in YYYY-MM-DD. Defaults to run_dongchedi_daily.py behavior.")
    parser.add_argument(
        "--publish-target",
        choices=["none", "confluence", "feishu"],
        default="confluence",
        help="Publish destination after local artifact generation.",
    )
    parser.add_argument("--refresh-source", action="store_true", help="Refresh the latest Dongchedi source CSV before generating the report.")
    parser.add_argument("--refresh-source-strict", action="store_true", help="Enable strict refresh validation.")
    parser.add_argument("--refresh-source-min-success-rate", type=float, default=0.60, help="Minimum refresh success rate used with --refresh-source-strict.")
    parser.add_argument("--refresh-source-min-successes", type=int, default=1, help="Minimum refreshed series count used with --refresh-source-strict.")
    parser.add_argument("--no-backfill-missing", action="store_true", help="Disable auto backfill for missing days when --date is not provided.")
    parser.add_argument("--feishu-document-id", default="", help="Optional Feishu doc token override.")
    parser.add_argument("--feishu-parent-block-id", default="", help="Optional Feishu parent block id override.")
    parser.add_argument("--feishu-dry-run", action="store_true", help="Preview Feishu publish payload without calling Feishu API.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not PYTHON_EXE.exists():
        raise RuntimeError(f"Python executable not found: {PYTHON_EXE}")

    generate_cmd = [str(PYTHON_EXE), str(RUN_DAILY), "--skip-confluence"]
    if args.date:
        generate_cmd.extend(["--date", args.date])
    if args.refresh_source:
        generate_cmd.append("--refresh-source")
    if args.refresh_source_strict:
        generate_cmd.extend(
            [
                "--refresh-source-strict",
                "--refresh-source-min-success-rate",
                str(args.refresh_source_min_success_rate),
                "--refresh-source-min-successes",
                str(args.refresh_source_min_successes),
            ]
        )
    if args.no_backfill_missing:
        generate_cmd.append("--no-backfill-missing")

    _run_command(generate_cmd)

    if args.publish_target == "none":
        print("Publish target: none")
        print("Artifacts generated locally. No remote publish executed.")
        return 0

    if args.publish_target == "confluence":
        _run_command([str(PYTHON_EXE), str(PUSH_CONFLUENCE)])
        print("Publish target: confluence")
        return 0

    feishu_cmd = [str(PYTHON_EXE), str(PUSH_FEISHU)]
    if args.date:
        feishu_cmd.extend(["--date", args.date])
    if args.feishu_document_id:
        feishu_cmd.extend(["--document-id", args.feishu_document_id])
    if args.feishu_parent_block_id:
        feishu_cmd.extend(["--parent-block-id", args.feishu_parent_block_id])
    if args.feishu_dry_run:
        feishu_cmd.append("--dry-run")
    _run_command(feishu_cmd)
    print("Publish target: feishu")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)

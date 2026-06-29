import argparse
import json
from pathlib import Path


def build_plan(source: str, dry_run: bool) -> dict:
    return {
        "skill": "dcc-rpa-assessment",
        "source": source,
        "dry_run": dry_run,
        "expected_columns": [
            "data_type",
            "personal_data_class",
            "important_data_class",
            "grading_level",
            "source",
            "collection",
            "in_vehicle_storage",
            "vehicle_to_cloud_transmission",
            "backend_usage",
            "gap_notes",
        ],
        "status": "skeleton",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Skeleton runner for dcc-rpa-assessment")
    parser.add_argument("--source", required=True, help="Confluence URL, page ID, or local evidence path")
    parser.add_argument("--output", help="Optional JSON plan output path")
    parser.add_argument("--dry-run", action="store_true", help="Print the execution plan only")
    args = parser.parse_args()

    plan = build_plan(args.source, args.dry_run)
    print(json.dumps(plan, ensure_ascii=True, indent=2))

    if args.output:
        Path(args.output).write_text(json.dumps(plan, ensure_ascii=True, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

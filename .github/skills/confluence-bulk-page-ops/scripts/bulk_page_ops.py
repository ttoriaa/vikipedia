import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser(description="Skeleton runner for confluence-bulk-page-ops")
    parser.add_argument("--instance", choices=["atc", "cc"], required=True)
    parser.add_argument("--root-page", required=True)
    parser.add_argument("--operation", choices=["read", "labels", "body-replace", "restrictions-template"], required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(vars(args) | {"skill": "confluence-bulk-page-ops", "status": "skeleton"}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

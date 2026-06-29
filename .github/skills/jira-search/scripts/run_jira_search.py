import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser(description="Skeleton runner for jira-search")
    parser.add_argument("--project", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(vars(args) | {"skill": "jira-search", "status": "skeleton"}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

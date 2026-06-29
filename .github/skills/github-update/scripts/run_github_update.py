import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser(description="Skeleton runner for github-update")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--intent", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(vars(args) | {"skill": "github-update", "status": "skeleton"}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

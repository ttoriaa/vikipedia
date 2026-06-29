#!/usr/bin/env python3
"""Repo-level entrypoint for the daily market news skill workflow."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET_SCRIPT = (
    REPO_ROOT
    / ".github"
    / "skills"
    / "daily-market-news-research"
    / "templates"
    / "daily-market-news-research"
    / "scripts"
    / "run_daily_market_news_research.py"
)


def main() -> int:
    if not TARGET_SCRIPT.exists():
        raise FileNotFoundError(f"Target skill script not found: {TARGET_SCRIPT}")
    sys.argv[0] = str(TARGET_SCRIPT)
    runpy.run_path(str(TARGET_SCRIPT), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

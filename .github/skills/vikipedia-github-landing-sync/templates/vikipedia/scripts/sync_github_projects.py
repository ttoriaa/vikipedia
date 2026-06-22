#!/usr/bin/env python3
"""Sync public GitHub repositories into a JSON feed used by the landing page."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request


GRAPHQL_ENDPOINT = "https://api.github.com/graphql"


def github_get_json(url: str, token: str | None) -> Any:
    req = request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "vikipedia-sync-bot")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    with request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def github_graphql(query: str, variables: dict[str, Any], token: str) -> Any:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = request.Request(GRAPHQL_ENDPOINT, data=payload, method="POST")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "vikipedia-sync-bot")
    req.add_header("Authorization", f"Bearer {token}")

    with request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if data.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {data['errors']}")
    return data.get("data") or {}


def normalize_homepage(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return f"https://{value}"


def has_any_homepage(repo: dict[str, Any]) -> bool:
    return normalize_homepage(repo.get("homepage")) is not None


def is_pages_homepage(url: str | None, username: str) -> bool:
    if not url:
        return False
    normalized = url.strip().lower()
    return f"{username.lower()}.github.io" in normalized


def is_github_pages_project(repo: dict[str, Any], username: str) -> bool:
    if bool(repo.get("has_pages")):
        return True
    homepage = normalize_homepage(repo.get("homepage"))
    return is_pages_homepage(homepage, username)


def is_eligible_project(repo: dict[str, Any], username: str, include_homepage_any_domain: bool) -> bool:
    if is_github_pages_project(repo, username):
        return True
    if include_homepage_any_domain and has_any_homepage(repo):
        return True
    return False


def build_project(repo: dict[str, Any], username: str) -> dict[str, Any]:
    homepage = normalize_homepage(repo.get("homepage"))
    name = repo.get("name") or ""
    pages_guess = f"https://{username}.github.io/{name}/"

    if homepage:
        url = homepage
        url_type = "homepage"
    elif repo.get("has_pages"):
        url = pages_guess
        url_type = "pages"
    else:
        url = repo.get("html_url") or f"https://github.com/{username}/{name}"
        url_type = "repo"

    topics = repo.get("topics") or []
    category = topics[0].replace("-", " ").title() if topics else "Project"

    return {
        "name": name,
        "description": (repo.get("description") or "").strip(),
        "url": url,
        "url_type": url_type,
        "target_label": "Live" if url_type in {"homepage", "pages"} else "Repo",
        "repo_url": repo.get("html_url") or "",
        "language": repo.get("language") or "",
        "category": category,
        "pushed_at": repo.get("pushed_at") or "",
    }


def build_project_board(board: dict[str, Any], owner_login: str) -> dict[str, Any]:
    return {
        "name": (board.get("title") or "Untitled Project Board").strip(),
        "description": (board.get("shortDescription") or "").strip(),
        "url": board.get("url") or f"https://github.com/users/{owner_login}/projects",
        "url_type": "project_board",
        "target_label": "Board",
        "repo_url": "",
        "language": "GitHub Project",
        "category": "Project Board",
        "pushed_at": board.get("updatedAt") or "",
    }


def fetch_repositories(username: str, token: str | None) -> list[dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    page = 1

    while True:
        qs = parse.urlencode({"per_page": 100, "sort": "updated", "page": page})
        url = f"https://api.github.com/users/{username}/repos?{qs}"
        batch = github_get_json(url, token)
        if not isinstance(batch, list) or not batch:
            break

        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    return repos


def fetch_project_boards(username: str, token: str | None, limit: int) -> list[dict[str, Any]]:
        if limit <= 0:
                return []
        if not token:
                print("Skipping GitHub Projects sync because GITHUB_TOKEN is not set.")
                return []

        query = """
        query($login: String!, $first: Int!) {
            user(login: $login) {
                login
                projectsV2(first: $first, orderBy: {field: UPDATED_AT, direction: DESC}) {
                    nodes {
                        title
                        shortDescription
                        public
                        closed
                        number
                        url
                        updatedAt
                    }
                }
            }
            organization(login: $login) {
                login
                projectsV2(first: $first, orderBy: {field: UPDATED_AT, direction: DESC}) {
                    nodes {
                        title
                        shortDescription
                        public
                        closed
                        number
                        url
                        updatedAt
                    }
                }
            }
        }
        """

        try:
                data = github_graphql(query, {"login": username, "first": limit}, token)
        except (RuntimeError, error.HTTPError, error.URLError) as exc:
                print(f"Skipping GitHub Projects sync because GraphQL lookup failed: {exc}")
                return []

        owner = data.get("user") or data.get("organization") or {}
        owner_login = owner.get("login") or username
        nodes = ((owner.get("projectsV2") or {}).get("nodes") or [])
        return [
                board
                for board in nodes
                if isinstance(board, dict)
                and bool(board.get("public"))
                and not bool(board.get("closed"))
        ]


def parse_timestamp(value: str) -> datetime:
        if not value:
                return datetime.min.replace(tzinfo=timezone.utc)
        try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
                return datetime.min.replace(tzinfo=timezone.utc)


def sync(
    username: str,
    output_path: Path,
    limit: int,
    token: str | None,
    include_homepage_any_domain: bool,
    include_project_boards: bool,
    project_board_limit: int,
) -> int:
    repos = fetch_repositories(username, token)

    filtered = [
        repo
        for repo in repos
        if not repo.get("fork")
        and not repo.get("private")
        and not repo.get("archived")
        and repo.get("name") != f"{username}.github.io"
        and is_eligible_project(repo, username, include_homepage_any_domain)
    ]

    projects = [build_project(repo, username) for repo in filtered]

    if include_project_boards:
        project_boards = fetch_project_boards(username, token, project_board_limit)
        projects.extend(build_project_board(board, username) for board in project_boards)

    projects.sort(key=lambda project: parse_timestamp(project.get("pushed_at") or ""), reverse=True)
    projects = projects[:limit]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": f"https://github.com/{username}",
        "projects": projects,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(projects)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync GitHub repositories to landing page JSON feed")
    parser.add_argument("--username", default=os.getenv("GITHUB_SYNC_USERNAME", "ttoriaa"))
    parser.add_argument("--output", default="assets/github-projects.json")
    parser.add_argument("--limit", type=int, default=9)
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN", ""))
    parser.add_argument(
        "--include-homepage-any-domain",
        action="store_true",
        help=(
            "Also include repositories with any homepage URL, not only GitHub Pages. "
            "By default, only GitHub Pages projects are included."
        ),
    )
    parser.add_argument(
        "--include-project-boards",
        action="store_true",
        default=os.getenv("GITHUB_SYNC_INCLUDE_PROJECT_BOARDS", "false").lower() in {"1", "true", "yes"},
        help="Also include public GitHub Projects V2 boards when a GitHub token is available.",
    )
    parser.add_argument(
        "--project-board-limit",
        type=int,
        default=int(os.getenv("GITHUB_SYNC_PROJECT_BOARD_LIMIT", "20")),
        help="How many GitHub project boards to fetch before mixed sorting and truncation.",
    )
    args = parser.parse_args()

    count = sync(
        username=args.username,
        output_path=Path(args.output),
        limit=max(1, args.limit),
        token=args.token or None,
        include_homepage_any_domain=args.include_homepage_any_domain,
        include_project_boards=args.include_project_boards,
        project_board_limit=max(0, args.project_board_limit),
    )
    print(f"Synced {count} projects to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
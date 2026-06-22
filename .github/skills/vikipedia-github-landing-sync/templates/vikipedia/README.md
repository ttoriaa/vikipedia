Vikipedia GitHub Landing Sync Template

Files in this template:
- scripts/sync_github_projects.py
- .github/workflows/sync-github-projects.yml

Quick setup in target repo:
1. Copy scripts/sync_github_projects.py to scripts/sync_github_projects.py.
2. Copy .github/workflows/sync-github-projects.yml to .github/workflows/sync-github-projects.yml.
3. Ensure the landing page fetches assets/github-projects.json.
4. Optional repository variables:
   - GITHUB_SYNC_USERNAME (default: ttoriaa)
   - GITHUB_SYNC_LIMIT (default: 9)
   - GITHUB_SYNC_INCLUDE_HOMEPAGE_ANY_DOMAIN (default: false)
   - GITHUB_SYNC_INCLUDE_PROJECT_BOARDS (default: true)
   - GITHUB_SYNC_PROJECT_BOARD_LIMIT (default: 20)
5. Enable the workflow schedule or trigger workflow_dispatch manually.

Manual test:
- python scripts/sync_github_projects.py --username ttoriaa --output assets/github-projects.json --limit 9
- python scripts/sync_github_projects.py --username ttoriaa --output assets/github-projects.json --limit 9 --include-homepage-any-domain
- python scripts/sync_github_projects.py --username ttoriaa --output assets/github-projects.json --limit 9 --include-project-boards

Behavior:
- The script pulls public repositories from the GitHub REST API.
- When a GitHub token is available, it can also pull public GitHub Projects V2 boards through GraphQL.
- It filters out fork/private/archived repositories and keeps project sites suitable for the landing page.
- The workflow commits only when assets/github-projects.json changed.
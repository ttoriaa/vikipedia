# confluence-search

## Purpose
Search CC and ATC Confluence content through a local script contract.

## Package Contents
- `SKILL.md`
- `README.md`
- `UAT.md`
- `UAT.meta.json`
- `scripts/search_from_confluence.py`
- `scripts/confluence_direct_client.py`

## Environment Variables
- `ATC_CONFLUENCE_BASE_URL`
- `ATC_CONFLUENCE_TOKEN`
- `CC_CONFLUENCE_BASE_URL`
- `CC_CONFLUENCE_TOKEN`

## Local Usage

```powershell
./.venv/Scripts/python.exe ./.github/skills/confluence-search/scripts/search_from_confluence.py --instance atc --query "keyword" --dry-run
```

```powershell
./.venv/Scripts/python.exe ./.github/skills/confluence-search/scripts/search_from_confluence.py --instance atc --mode cql --cql "type = \"page\" and text ~ \"charging\"" --limit 5
```

```powershell
./.venv/Scripts/python.exe ./.github/skills/confluence-search/scripts/search_from_confluence.py --instance atc --mode page-tree --page-ref 8120367860 --max-depth 2
```

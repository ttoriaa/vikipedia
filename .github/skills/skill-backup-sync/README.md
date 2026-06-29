# skill-backup-sync

## Purpose
Publish or refresh local skill backup contracts into an ATC Confluence backup index.

## Package Contents
- `SKILL.md`
- `README.md`
- `UAT.md`
- `UAT.meta.json`
- `scripts/publish_skill_backup_pages.py`

## Local Usage

```powershell
./.venv/Scripts/python.exe ./scripts/publish_skill_backup_pages.py --instance atc --root-page 8120367860 --skill confluence-search --skill skill-backup-sync --dry-run
```

```powershell
./.venv/Scripts/python.exe ./scripts/publish_skill_backup_pages.py --instance atc --root-page 8120367860 --apply
```

# confluence-update

## Purpose
Prepare controlled Confluence write operations with explicit scope and traceable intent.

## Package Contents
- `SKILL.md`
- `README.md`
- `UAT.md`
- `UAT.meta.json`
- `scripts/update_confluence.py`

## Local Usage

```powershell
./.venv/Scripts/python.exe ./.github/skills/confluence-update/scripts/update_confluence.py --instance atc --page-ref 12345 --replace-old "old text" --replace-new "new text"
```

```powershell
./.venv/Scripts/python.exe ./.github/skills/confluence-update/scripts/update_confluence.py --instance atc --page-ref 12345 --append-file .\snippet.html --apply
```

```powershell
./.venv/Scripts/python.exe ./.github/skills/confluence-update/scripts/update_confluence.py --instance atc --page-ref https://atc.bmwgroup.net/confluence/pages/viewpage.action?pageId=8120367860 --output-body-file .\reports\task_logs\preview.html
```

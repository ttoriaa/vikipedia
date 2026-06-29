# jira-update

## Purpose
Prepare controlled Jira write operations with explicit intent.

## Package Contents
- `SKILL.md`
- `README.md`
- `UAT.md`
- `UAT.meta.json`
- `scripts/run_jira_update.py`

## Local Usage

```powershell
./.venv/Scripts/python.exe ./.github/skills/jira-update/scripts/run_jira_update.py --issue SECMGTCN-123 --intent "update summary" --summary "New summary"
```

```powershell
./.venv/Scripts/python.exe ./.github/skills/jira-update/scripts/run_jira_update.py --issue SECMGTCN-123 --intent "append review note" --comment-file .\note.md --apply
```

## Environment Variables
- `JIRA_BASE_URL`
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`
- `JIRA_AUTH_TYPE`

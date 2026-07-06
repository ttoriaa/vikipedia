# Foundation Model Release Watch - Teammate Guide

This page explains how teammates can run and operate the `foundation-model-release-watch` skill.

## 1. What This Skill Does

- Tracks new releases and important updates across major foundation-model providers.
- Current default providers: `openai, anthropic, google, deepseek, moonshot, glm, qwen`.
- Produces:
  - Markdown report: `reports/foundation_model_release_watch/<date>/foundation_model_release_watch.md`
  - JSON report: `reports/foundation_model_release_watch/<date>/foundation_model_release_watch.json`
  - Latest snapshot: `reports/foundation_model_release_watch/latest.md`

## 2. Local Run (Windows)

Prerequisites:
- Repository cloned
- Python environment available (`.venv`)

Run a quick dry run:

```powershell
Set-Location "C:/Users/<you>/.../vikipedia-agents"
./.venv/Scripts/python.exe scripts/run_foundation_model_release_watch.py --dry-run true
```

Run a weekly-style report manually:

```powershell
Set-Location "C:/Users/<you>/.../vikipedia-agents"
./.venv/Scripts/python.exe scripts/run_foundation_model_release_watch.py `
  --cadence weekly `
  --window-days 7 `
  --providers openai,anthropic,google,deepseek,moonshot,glm,qwen `
  --max-items 5 `
  --language bilingual `
  --dry-run false
```

Useful optional arguments:
- `--date YYYY-MM-DD`
- `--emit-json <path>`
- `--request-timeout <seconds>`

## 3. Manual Trigger in GitHub Actions

Workflow file:
- `.github/workflows/sync-foundation-model-release-watch.yml`

From GitHub UI:
1. Open repository `Actions` tab.
2. Select `Sync Foundation Model Release Watch`.
3. Click `Run workflow`.
4. Optional inputs:
   - `cadence`
   - `window_days`
   - `providers`
   - `max_items`
   - `language`

The workflow auto-commits report changes under `reports/foundation_model_release_watch` when there are updates.

## 4. Scheduled Run Configuration

Default schedule in workflow:
- `cron: "10 1 * * 1"` (UTC)
- Equivalent to Monday morning in Beijing time.

You can adjust schedule directly in:
- `.github/workflows/sync-foundation-model-release-watch.yml`

Optional repo variables (Settings -> Secrets and variables -> Actions -> Variables):
- `RELEASE_WATCH_CADENCE`
- `RELEASE_WATCH_WINDOW_DAYS`
- `RELEASE_WATCH_PROVIDERS`
- `RELEASE_WATCH_MAX_ITEMS`
- `RELEASE_WATCH_LANGUAGE`

## 5. Troubleshooting

- No updates found:
  - Expand `--window-days` (for example from `7` to `14`).
- Many source failures:
  - Increase `--request-timeout`.
  - Retry later when network is stable.
- Output exists but no commit from workflow:
  - Workflow commits only when report files changed.

## 6. Ownership and Handoff

- Skill definition: `.github/skills/foundation-model-release-watch/SKILL.md`
- Runner script: `scripts/run_foundation_model_release_watch.py`
- Automation workflow: `.github/workflows/sync-foundation-model-release-watch.yml`

If you add providers, update all three places for consistency.

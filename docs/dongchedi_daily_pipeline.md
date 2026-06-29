# Dongchedi Daily Charging Pipeline

## Goal

Generate a daily charging-performance report for pure EV models above 20万 and publish each day to a dedicated Confluence child page at 09:00 local time.

## What This Pipeline Does

1. Loads the latest `dongchedi_full_configs_YYYY-MM-DD.csv` file.
2. Optional: refreshes source rows from live Dongchedi params pages (`__NEXT_DATA__`) and writes `dongchedi_full_configs_<run_date>.csv`.
3. Keeps only pure EV rows (`动力形式` contains `纯电`).
4. Applies price filter (`价格(万元) > 20`) using `dongchedi_price_map.csv`.
5. Normalizes charging field name:
- `快充电量(%)` -> `充电电量`
6. Keeps yesterday models when they disappear today (`昨日沿用(当日未出现)`).
7. Builds daily outputs in `reports/dongchedi_daily/YYYY-MM-DD/`.
8. Creates or updates a child page named `懂车帝充电日报 YYYY-MM-DD` under the configured Confluence parent page.
9. Can also publish a GitHub Pages site from the generated daily reports and visualization dashboard.

## Required Files

- Source CSV in workspace root:
- `dongchedi_full_configs_YYYY-MM-DD.csv`

- Price map CSV in workspace root:
- `dongchedi_price_map.csv`

If price map is missing, first run auto-creates a template and exits.

### Price Map Schema

```csv
车系ID,车型,价格(万元),价格来源,更新时间
3503,埃安AION LX PLUS 80 智尊版,26.66,手动维护,2026-06-08
...
```

## Environment Variables

Add to `.env`:

```env
CONFLUENCE_DAILY_PAGE_ID=<target-page-id>
CONFLUENCE_DAILY_PARENT_PAGE_ID=<parent-page-id>
```

Rules:
- If `CONFLUENCE_DAILY_PARENT_PAGE_ID` is set, the script treats it as the source of truth and publishes each day under that parent.
- If a child page for the same date already exists under that parent, the script updates it in place.
- `CONFLUENCE_DAILY_PAGE_ID` is optional fallback behavior only when no parent page is configured.

The following are already used by existing Confluence MCP server and reused here:

```env
CONFLUENCE_BASE_URL=https://<your-domain>.atlassian.net/wiki
CONFLUENCE_EMAIL=<your-email>
CONFLUENCE_API_TOKEN=<your-api-token>
CONFLUENCE_AUTH_TYPE=auto
```

## .env vs PowerShell $env

- `run_dongchedi_daily.py` and `push_dongchedi_to_confluence.py` load `.env` internally via `python-dotenv`.
- Therefore, checking `$env:CONFLUENCE_*` in PowerShell alone may show empty values even when `.env` is correct.
- Use this precheck as source of truth:

```powershell
.\.venv\Scripts\python.exe .\scripts\precheck_confluence_env.py --mode pipeline
```

- Optional (only when you need `$env` visible in current shell for debugging):

```powershell
. .\scripts\load_env_into_session.ps1 -ShowKeys
```

## Commands

Dry run (local files only):

```powershell
.\.venv\Scripts\python.exe .\scripts\run_dongchedi_daily.py --dry-run
```

Generate local files, skip Confluence:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_dongchedi_daily.py --skip-confluence
```

Generate with live upstream refresh first:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_dongchedi_daily.py --skip-confluence --refresh-source
```

Generate with strict mode (fail when refresh success rate is too low):

```powershell
.\.venv\Scripts\python.exe .\scripts\run_dongchedi_daily.py --skip-confluence --refresh-source --refresh-source-strict --refresh-source-min-success-rate 0.60 --refresh-source-min-successes 1
```

Full run (includes Confluence update):

```powershell
.\.venv\Scripts\python.exe .\scripts\run_dongchedi_daily.py
```

## Outputs

For each date folder:

- `filtered.csv`
- `filtered.json`
- `summary.md`
- `summary.html`
- `confluence_section.html`
- `refresh_log.json` (refresh full result and per-series status)
- `refresh_failures.json` (failed series details only, per date)

Global log:

- `reports/dongchedi_daily/run_log.jsonl`

GitHub Pages site build output:

- `site/index.html`
- `site/latest/charging_visualization_dashboard.html`
- `site/reports/YYYY-MM-DD/`

## Scheduling (Windows Task Scheduler)

Use one daily task at 09:00 with this command sequence:

```powershell
cd "c:\Users\Q653867\OneDrive - BMW Group\Desktop\V\vikipedia-agents"
.\.venv\Scripts\python.exe .\scripts\run_dongchedi_daily.py --dry-run
.\.venv\Scripts\python.exe .\scripts\push_dongchedi_to_confluence.py
```

Or run helper script:

```powershell
.\scripts\register_dongchedi_daily_task.ps1 -TaskName "DongchediDailyChargingReport" -Time "09:00"
```

The registered task runs the full pipeline in order:
- regenerate the latest daily artifacts
- publish the latest report to the configured Confluence parent page as a date-specific child page

## GitHub Pages Publishing

If you want the report site on GitHub, enable Pages from GitHub Actions and keep the workflow at `.github/workflows/dongchedi-pages.yml`.

The workflow:

- runs daily at 01:00 UTC, which is 09:00 in China Standard Time
- refreshes source data from live Dongchedi params pages
- runs in strict refresh mode (`--refresh-source-strict --refresh-source-min-success-rate 0.60`); publish is blocked when refresh quality is too low
- generates the latest daily report and chart
- assembles a static site under `site/`
- deploys that site to GitHub Pages

## Notes

- First run must have valid price data to enforce `>20万` filter.
- If the same day is rerun, the same child page for that date is updated in place.
- The script does not send emails; it updates Confluence only.

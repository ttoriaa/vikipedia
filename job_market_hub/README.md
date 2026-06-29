# Job Market Hub

A focused job aggregation site for:
- Vehicle Project Management
- Data Product Manager
- Data Project Management
- Technical Presales Support

## Data Update

Generate live site data into `job_market_hub/data/jobs.json`:

```powershell
.\.venv\Scripts\python.exe .\scripts\update_job_market_data.py
```

Default behavior is `incremental` mode:
- Merge new jobs into the main deduplicated library: `job_market_hub/data/jobs.json`
- Save today's snapshot into: `job_market_hub/data/history/YYYY-MM-DD/jobs.json`
- Update snapshot index for date review: `job_market_hub/data/snapshots_index.json`

### Optional Arguments

```powershell
.\.venv\Scripts\python.exe .\scripts\update_job_market_data.py \
  --max-pages 2 \
  --city-codes 101010100,101020100,101280100 \
  --csv-glob "job_market_hub/data/raw/*.csv" \
  --mode incremental \
  --keep-days 120
```

### Incremental And Snapshot Controls

```powershell
# Use a fixed snapshot date (useful for reruns)
.\.venv\Scripts\python.exe .\scripts\update_job_market_data.py --snapshot-date 2026-06-16

# Keep all snapshots (no pruning)
.\.venv\Scripts\python.exe .\scripts\update_job_market_data.py --keep-days 0

# Replace mode: overwrite main library with current run only
.\.venv\Scripts\python.exe .\scripts\update_job_market_data.py --mode replace
```

## Date Review In UI

Homepage includes a "日期回看" selector:
- `最新数据` reads `job_market_hub/data/jobs.json`
- Specific dates read from `job_market_hub/data/snapshots_index.json`
- Selected date loads snapshot file under `job_market_hub/data/history/`

## Data Sources

- BOSS search pages (best effort scraping, may require valid cookie / network access)
- Local exported CSV files dropped into `job_market_hub/data/raw/`

## Application Tracking

The application status board is stored in browser LocalStorage:
- 未投递
- 已投递
- 面试中
- Offer

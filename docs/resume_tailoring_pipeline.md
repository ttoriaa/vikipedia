# Resume Tailoring Pipeline

This pipeline generates reusable resume tailoring outputs for changing JD/resume inputs.

## What It Produces

For each run, the script outputs three versions by default:
- `conservative`
- `balanced`
- `aggressive`

Supported file outputs:
- `HTML`
- `PDF` (via local Edge/Chrome headless print)
- `Word (.docx)`
- Optional: `JSON`, `Markdown`

Output folder default:
- `reports/resume_tailoring/<YYYY-MM-DD>/`

## Script

- `scripts/tailor_resume_for_jd.py`

## Inputs

Provide either raw text or files:
- Resume: `--resume-text` or `--resume-file`
- JD: `--jd-text` or `--jd-file`

Optional:
- `--job-title` for display and positioning
- `--language` in `zh|en|bilingual`
- `--formats` in `html,pdf,word,json,md`

## Quick Start

```powershell
Set-Location "C:/Users/Q653867/OneDrive - BMW Group/Desktop/V/vikipedia-agents"
.\.venv\Scripts\python.exe .\scripts\tailor_resume_for_jd.py `
  --resume-file .\resume_extracted.txt `
  --jd-file .\job_market_hub\data\raw\sample_jd.txt `
  --job-title "AI Strategy" `
  --language zh `
  --formats html,pdf,word,json,md
```

## Dry Run

Use dry run to verify extracted sections and version coverage without writing files:

```powershell
.\.venv\Scripts\python.exe .\scripts\tailor_resume_for_jd.py `
  --resume-file .\resume_extracted.txt `
  --jd-text "负责AI产品策略、跨团队协同、数据分析与项目交付" `
  --dry-run
```

## OpenAI Behavior

- If `OPENAI_API_KEY` is set, script tries model generation (`--model`, default `gpt-4o-mini`).
- If API key is missing or API fails, script falls back to deterministic rule-based rewriting.

## Notes

- PDF export requires local Edge/Chrome executable available in PATH or standard install locations.
- The script only rewrites with available resume facts and does not invent new companies/projects.
- Tune output style by selecting versions in `--versions`, e.g. `conservative,balanced`.

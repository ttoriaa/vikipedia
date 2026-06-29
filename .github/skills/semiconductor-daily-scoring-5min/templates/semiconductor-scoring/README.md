# Semiconductor Daily Scoring Template

This template provides a runnable baseline for daily semiconductor scoring.

## Files
- `scripts/run_daily_semiconductor_scoring.py`: fetch evidence, map signals, score, and render markdown.
- `config/default_universe.json`: factor definitions, company-type weights, and preset universes.
- `.github/workflows/semiconductor-daily-scoring.yml`: scheduled/manual automation.
- `report_viewer.html`: visual dashboard for generated JSON/Markdown outcomes.

## Quick Start

```bash
python scripts/run_daily_semiconductor_scoring.py --universe core3 --dry-run
python scripts/run_daily_semiconductor_scoring.py --universe ai6 --dry-run
python scripts/run_daily_semiconductor_scoring.py --universe core3 --dry-run --emit-json reports/semiconductor_daily/latest.json
```

Custom companies:

```bash
python scripts/run_daily_semiconductor_scoring.py \
  --companies "000660.KS:sg:IDM,TSM:sg:Foundry,ASML:sg:Equipment" \
  --dry-run \
  --emit-json reports/semiconductor_daily/custom_latest.json
```

Generate and commit report:

```bash
python scripts/run_daily_semiconductor_scoring.py --universe ai6 --dry-run=false --auto-commit
```

## Output
Reports are written to:
- `reports/semiconductor_daily/semiconductor_daily_YYYY-MM-DD.md`
- Optional machine-readable JSON:
- `reports/semiconductor_daily/*.json` (when `--emit-json` is provided)

## Result Web Viewer
Open:
- `report_viewer.html`

Default behavior:
- Tries loading `./reports/semiconductor_daily/semiconductor_daily_2026-06-22.md` first.
- Falls back to `./reports/semiconductor_daily/latest_skhynix.json` if Markdown is unavailable.
- If browser blocks local fetch, use **Load Local Markdown/JSON** and select a generated file.

Recommended local static server (optional):

```bash
python -m http.server 8090
```

Then open:
- `http://localhost:8090/report_viewer.html`

Generated report files can be opened directly too:
- `reports/semiconductor_daily/semiconductor_daily_YYYY-MM-DD.md`

## Notes
- If a source cannot be fetched, the related factor remains neutral (`0`) and is marked `source_unavailable`.
- The key 6 factors are auto-filled using keyword polarity + price-move thresholds + company-type-aware rules.
- This implementation is evidence-driven and intentionally conservative for unknown fields.

## Workflow Dispatch Inputs
`semiconductor-daily-scoring.yml` supports:
- `universe`: `core3` or `ai6`
- `companies`: override universe with custom list `SYMBOL:SCOPE:TYPE,...`
- `emit_json`: optional JSON output path
- `date`, `dry_run`, `auto_commit`

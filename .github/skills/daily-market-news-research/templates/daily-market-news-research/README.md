# Daily Market News Research Template

This template provides a runnable baseline for daily multi-market news research.

## Files
- `scripts/run_daily_market_news_research.py`: fetch public news sources, deduplicate, classify, and render Markdown/JSON.
- `config/default_sources.json`: market locale settings, default watchlists, and theme keywords.
- `README.md`: quick start and output contract.

## Quick Start

Run from the repository root:

```bash
python scripts/run_daily_market_news.py --dry-run true --mode mixed --markets us,cn,kr,hk
python scripts/run_daily_market_news.py --dry-run false --mode mixed --markets us,cn,kr,hk
python .github/skills/daily-market-news-research/templates/daily-market-news-research/scripts/run_daily_market_news_research.py --dry-run
python .github/skills/daily-market-news-research/templates/daily-market-news-research/scripts/run_daily_market_news_research.py --mode mixed --markets us,cn,kr,hk --themes semiconductor,"ai compute",memory,gold --dry-run
python .github/skills/daily-market-news-research/templates/daily-market-news-research/scripts/run_daily_market_news_research.py --symbols NVDA,TSM,000660.KS,0700.HK --emit-json reports/daily_market_news/latest.json --dry-run
```

VS Code tasks are available in `.vscode/tasks.json`:
- `Daily Market News: Dry Run`
- `Daily Market News: Run`

## Output
Reports are written to:
- `reports/daily_market_news/YYYY-MM-DD/daily_market_news_YYYY-MM-DD.md`
- Optional machine-readable JSON:
- `reports/daily_market_news/YYYY-MM-DD/daily_market_news_YYYY-MM-DD.json`

## Notes
- Default source policy is public-web-first and tightened to:
	- Google News RSS
	- Yahoo Finance RSS
	- Exchange announcements (market-specific site filters, plus SEC Atom for US)
- If a source cannot be fetched, the related item batch is skipped and the report records the failure.
- The template is conservative: it only collects and organizes evidence, it does not publish anywhere by itself.

## Workflow Inputs
The script supports:
- `date`
- `mode`: `watchlist`, `theme`, or `mixed`
- `markets`: any combination of `us`, `cn`, `kr`, `hk`
- `symbols`: comma-separated watchlist symbols
- `themes`: comma-separated theme keywords
- `max_items`
- `language`: `zh`, `en`, or `bilingual`
- `dry_run`
- `emit_json`
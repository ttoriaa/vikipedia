# Skills Index

This index helps team members quickly discover and invoke available skills.

## Local Deployment

Skills are locally available to Copilot in this workspace when they live under `.github/skills/<skill-name>/SKILL.md`.

To deploy a new skill locally:
1. Copy `.github/skills/reusable-skill-template/` to `.github/skills/<your-skill-name>/`.
2. Update `SKILL.md` frontmatter: `name`, `description`, `argument-hint`.
3. Add any bundled scripts/templates under the same folder.
4. Add an entry in this index so the skill is easy to discover.
5. Reload the VS Code window if Copilot does not pick up the new skill immediately.

## Dongchedi Skills

### 1. dongchedi-charging-confluence-pipeline

Use when:
- You want one workflow to run Dongchedi charging daily processing and publish/update Confluence.

Path:
- [dongchedi-charging-confluence-pipeline/SKILL.md](dongchedi-charging-confluence-pipeline/SKILL.md)

Quick invoke:
- `/dongchedi-charging-confluence-pipeline`
- `/dongchedi-charging-confluence-pipeline date=2026-06-17 publish=false`

### 2. dongchedi-charging-performance-summary

Use when:
- You need extraction and structured comparison of charging fields from Dongchedi parameter pages.

Path:
- [dongchedi-charging-performance-summary/SKILL.md](dongchedi-charging-performance-summary/SKILL.md)

Quick invoke:
- `/dongchedi-charging-performance-summary 对这 5 个懂车帝 URL 生成充电性能对比总结`

### 3. dongchedi-site-sync-after-daily

Use when:
- You have finished daily CSV and Confluence update, and now want to sync the website pages.
- You need to refresh data.html, dashboard.html, and insights.html together.

Path:
- [dongchedi-site-sync-after-daily/SKILL.md](dongchedi-site-sync-after-daily/SKILL.md)

Quick invoke:
- `/dongchedi-site-sync-after-daily date=2026-06-17`
- `/dongchedi-site-sync-after-daily date=2026-06-17 deploy=false`

### 4. vikipedia-github-landing-sync

Use when:
- You want `ttoriaa/vikipedia` to periodically detect new public GitHub project sites and refresh the landing page feed.
- You need a reusable script + GitHub Actions workflow for `assets/github-projects.json`.

Path:
- [vikipedia-github-landing-sync/SKILL.md](vikipedia-github-landing-sync/SKILL.md)

Quick invoke:
- `/vikipedia-github-landing-sync username=ttoriaa limit=9 include_project_boards=true install_workflow=true`
- `/vikipedia-github-landing-sync username=ttoriaa include_homepage_any_domain=true include_project_boards=true auto_commit=true auto_push=true`

### 5. semiconductor-daily-scoring-5min

Use when:
- You need a repeatable 5-minute daily scoring flow for semiconductor companies.
- You want company-type weighted evaluation (Fabless/Foundry/IDM/Equipment/OSAT) with explainable evidence.
- You want Markdown daily report output with optional automation via workflow.

Path:
- [semiconductor-daily-scoring-5min/SKILL.md](semiconductor-daily-scoring-5min/SKILL.md)

Quick invoke:
- `/semiconductor-daily-scoring-5min universe=core3 dry_run=true`
- `/semiconductor-daily-scoring-5min universe=ai6 dry_run=false auto_commit=true auto_push=false`

### 6. daily-market-news-research

Use when:
- You need a repeatable daily market-news brief across US, China, Korea, and Hong Kong.
- You want both stock-watchlist and theme-based research in one skill.
- You need bilingual Markdown output with source links.

Path:
- [daily-market-news-research/SKILL.md](daily-market-news-research/SKILL.md)

Quick invoke:
- `/daily-market-news-research`
- `/daily-market-news-research mode=mixed markets=us cn kr hk themes=semiconductor,ai compute,memory,gold language=bilingual dry_run=true`

### 7. live-web-news-retry

Use when:
- You want to rerun direct web news collection after network connectivity recovers.
- You need fresh A/B/C HTML/Markdown/JSON output without relying on historical data tables.

Path:
- [live-web-news-retry/SKILL.md](live-web-news-retry/SKILL.md)

Quick invoke:
- `/live-web-news-retry`
- `/live-web-news-retry timeout=12 max_per_source=6`

## Compliance Skills

### 8. dcc-rpa-assessment

Use when:
- You need one merged CSV that keeps DCC classification columns and appends row-level processing behavior.

Path:
- [dcc-rpa-assessment/SKILL.md](dcc-rpa-assessment/SKILL.md)

### 9. pia-measures-bank-assessment

Use when:
- You want the final PIA Measures Bank V4.0 assessment table in English from feature evidence.

Path:
- [pia-measures-bank-assessment/SKILL.md](pia-measures-bank-assessment/SKILL.md)

### 10. confluence-search

Use when:
- You need read-only Confluence discovery, page-tree lookup, keyword search, or CQL retrieval for CC or ATC.

Path:
- [confluence-search/SKILL.md](confluence-search/SKILL.md)

Quick invoke:
- `/confluence-search instance=atc query=charging space_key=SECMGTCN`
- `/confluence-search instance=atc mode=page-tree page_ref=8120367860 max_depth=2`

### 11. confluence-update

Use when:
- You need controlled Confluence updates with explicit scope and traceable intent.

Path:
- [confluence-update/SKILL.md](confluence-update/SKILL.md)

Quick invoke:
- `/confluence-update instance=atc page_ref=8120367860 replace_old="foo" replace_new="bar"`
- `/confluence-update instance=atc page_ref=8120367860 append_file=.\snippet.html apply=true`

### 12. confluence-bulk-page-ops

Use when:
- You need bulk operations on one Confluence root page and its descendants.

Path:
- [confluence-bulk-page-ops/SKILL.md](confluence-bulk-page-ops/SKILL.md)

### 13. skill-backup-sync

Use when:
- You want to refresh the Confluence skill backup index from the local workspace skills.

Path:
- [skill-backup-sync/SKILL.md](skill-backup-sync/SKILL.md)

Quick invoke:
- `/skill-backup-sync instance=atc root_page=8120367860 skill=confluence-search`
- `/skill-backup-sync instance=atc root_page=8120367860 apply=true`

### 14. github-search

Use when:
- You need GitHub evidence retrieval for technical or compliance context.

Path:
- [github-search/SKILL.md](github-search/SKILL.md)

### 15. github-update

Use when:
- You need scoped, auditable GitHub-side write operations.

Path:
- [github-update/SKILL.md](github-update/SKILL.md)

### 16. jira-search

Use when:
- You need read-only Jira evidence retrieval.

Path:
- [jira-search/SKILL.md](jira-search/SKILL.md)

### 17. jira-update

Use when:
- You need controlled Jira updates with explicit intent.

Path:
- [jira-update/SKILL.md](jira-update/SKILL.md)

Quick invoke:
- `/jira-update issue=SECMGTCN-123 intent="update summary" summary="New summary"`
- `/jira-update issue=SECMGTCN-123 intent="append note" comment_file=.\note.md apply=true`

### 18. multi-source-search

Use when:
- You need a single answer synthesized from Confluence, GitHub, and Jira together.

Path:
- [multi-source-search/SKILL.md](multi-source-search/SKILL.md)

### 19. html-slide-deck-generator

Use when:
- You need to generate a standalone HTML slide deck that preserves PPT-style visual direction.
- You want an editable scaffold for fast wording and page design iteration.

Path:
- [html-slide-deck-generator/SKILL.md](html-slide-deck-generator/SKILL.md)

Quick invoke:
- `/html-slide-deck-generator source_ppt=./input/demo.pptx content_input=./.github/skills/html-slide-deck-generator/fixtures/sample_deck.json output_mode=scaffold`
- `/html-slide-deck-generator output_mode=final-deck deck_title="Q3 Strategy Review" language=bilingual`

### 20. ai-hardware-industry-chain

Use when:
- You need a reusable AI hardware value-chain map across GPU, HBM, advanced packaging, ABF, PCB, MLCC, and connectors.
- You want one output that combines representative companies, bottleneck analysis, bargaining power, and buyer-view BOM plus shortage probability.

Path:
- [ai-hardware-industry-chain/SKILL.md](ai-hardware-industry-chain/SKILL.md)

Quick invoke:
- `/ai-hardware-industry-chain perspective=buyer output=both include_bom=true include_shortage_prob=true`
- `/ai-hardware-industry-chain language=bilingual include_companies=true`
- `/ai-hardware-industry-chain perspective=buyer auto_procurement_actions=true risk_to_action_mode=conservative`

## Add New Skills

When adding a new skill:
1. Create a folder under `.github/skills/<skill-name>/`.
2. Add `SKILL.md` with complete frontmatter and usage guidance.
3. Append a new section in this index with purpose, path, and quick invoke examples.

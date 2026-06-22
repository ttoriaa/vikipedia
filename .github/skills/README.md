# Skills Index

This index helps team members quickly discover and invoke available skills.

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

## Add New Skills

When adding a new skill:
1. Create a folder under `.github/skills/<skill-name>/`.
2. Add `SKILL.md` with complete frontmatter and usage guidance.
3. Append a new section in this index with purpose, path, and quick invoke examples.

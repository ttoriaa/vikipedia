# Vikipedia Agents

精简导航，帮助团队快速发现并调用常用 Skill。

## Skills Quick Entry

### 1) dongchedi-charging-confluence-pipeline

用途:
- 触发懂车帝 charging 数据日常流程。
- 生成报告产物并更新 Confluence 页面。

技能文件:
- [.github/skills/dongchedi-charging-confluence-pipeline/SKILL.md](.github/skills/dongchedi-charging-confluence-pipeline/SKILL.md)

快速调用:
- Slash: `/dongchedi-charging-confluence-pipeline`
- 指定日期 dry-run: `/dongchedi-charging-confluence-pipeline date=2026-06-17 publish=false`
- 指定日期并发布: `/dongchedi-charging-confluence-pipeline date=2026-06-17 publish=true`
- 自然语言: `帮我跑懂车帝 charging 日报并更新 Confluence，日期用今天。`

关键参数:
- `date=YYYY-MM-DD`
- `publish=true|false` (default: `true`)
- `refresh_source=true|false` (default: `false`)
- `strict_refresh=true|false` (default: `false`)
- `no_backfill=true|false` (default: `true`)

前置要求 (publish=true):
- `CONFLUENCE_BASE_URL`
- `CONFLUENCE_EMAIL`
- `CONFLUENCE_API_TOKEN`
- `CONFLUENCE_DAILY_PARENT_PAGE_ID` or `CONFLUENCE_DAILY_PAGE_ID`

输出目录:
- `reports/dongchedi_daily/<date>/`
- 典型产物: `filtered.csv`, `filtered.json`, `summary.md`, `confluence_section.html`

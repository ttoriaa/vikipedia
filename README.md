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

### 4) Resume Tailor Studio (HTML + JD)

用途:
- 输入现有简历 HTML 链接（本地 `file:///` 或线上 `https://`）。
- 输入 JD 文本，或上传 JD 图片（OCR）。
- 生成保留原页面结构的新适配简历 HTML。

启动:
- `./.venv/Scripts/python.exe ./scripts/resume_tailor_web.py --port 8787`
- 浏览器打开: `http://127.0.0.1:8787`

说明:
- 默认输出目录: `reports/resume_tailoring/<date>_web/`
- 默认改写版本: `aggressive`
- 支持版本: `conservative|balanced|aggressive`
- 若仅上传 JD 图片，需要配置 `OPENAI_API_KEY`（可选 `OPENAI_BASE_URL`）

### 2) dongchedi-site-sync-after-daily

用途:
- 在当日懂车帝数据与 Confluence 更新完成后，同步网站页面。
- 一次更新 data.html、dashboard.html、insights.html 与最新可视化别名。

技能文件:
- [.github/skills/dongchedi-site-sync-after-daily/SKILL.md](.github/skills/dongchedi-site-sync-after-daily/SKILL.md)

快速调用:
- Slash: `/dongchedi-site-sync-after-daily date=2026-06-17`
- 本地预览不发布: `/dongchedi-site-sync-after-daily date=2026-06-17 deploy=false`
- 自然语言: `把今天懂车帝充电日报同步到网站，包括数据、可视化和趋势总结。`

### 3) vikipedia-github-landing-sync

用途:
- 检测 `ttoriaa` 公开 GitHub 仓库里新增的可展示项目站点。
- 定期更新 landing page `#sites` 区块依赖的 `assets/github-projects.json`。
- 为 `ttoriaa/vikipedia` 提供可复用的脚本和 GitHub Actions 模板。

技能文件:
- [.github/skills/vikipedia-github-landing-sync/SKILL.md](.github/skills/vikipedia-github-landing-sync/SKILL.md)

快速调用:
- Slash: `/vikipedia-github-landing-sync username=ttoriaa limit=9 include_project_boards=true install_workflow=true`
- 允许任意 homepage 域名: `/vikipedia-github-landing-sync username=ttoriaa include_homepage_any_domain=true`
- 一并同步 GitHub Projects 看板: `/vikipedia-github-landing-sync username=ttoriaa include_project_boards=true`
- 自然语言: `给 vikipedia landing page 加一个定时同步 GitHub 新项目的技能和 workflow。`

关键参数:
- `username=<github-user>`
- `limit=<max-projects>`
- `include_homepage_any_domain=true|false`
- `include_project_boards=true|false`
- `project_board_limit=<n>`
- `install_workflow=true|false`
- `auto_commit=true|false`
- `auto_push=true|false`

模板文件:
- `.github/skills/vikipedia-github-landing-sync/templates/vikipedia/scripts/sync_github_projects.py`
- `.github/skills/vikipedia-github-landing-sync/templates/vikipedia/.github/workflows/sync-github-projects.yml`

## Personal Knowledge Base

用途:
- 把对话产出、网站搭建过程、技能训练过程和任务日志汇总为可复用知识库快照。

命令:
- `./.venv/Scripts/python.exe ./scripts/build_personal_knowledge_base.py`
- 可选参数: `--date YYYY-MM-DD --top-skills 12 --recent-limit 15`

输出:
- `reports/knowledge_base/<date>/personal_kb.md`
- `reports/knowledge_base/<date>/personal_kb.json`
- `reports/knowledge_base/latest.md`
- `reports/knowledge_base/index.html`
- `reports/knowledge_base/latest.html`

定时更新:
- `./scripts/register_personal_kb_daily_task.ps1`
- 运行器: `./scripts/run_personal_kb_task_runner.ps1 -Mode run`

结构化决策日志:
- `./.venv/Scripts/python.exe ./scripts/add_decision_log_entry.py --title "title" --decision "decision"`
- 模板: `reports/knowledge_base/templates/decision_note_template.md`
- 输出: `reports/knowledge_base/notes/YYYY-MM-DD_decisions.md`

说明文档:
- `docs/personal_knowledge_base.md`

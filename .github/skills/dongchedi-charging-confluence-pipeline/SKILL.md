---
name: dongchedi-charging-confluence-pipeline
description: "触发懂车帝 charging 数据抓取并生成/更新 Confluence 页面。Use when you need Dongchedi daily charging crawl, report artifacts, and Confluence publishing in one workflow."
argument-hint: "可选参数: date=YYYY-MM-DD, publish=true|false, refresh_source=true|false, strict_refresh=true|false, no_backfill=true|false"
user-invocable: true
disable-model-invocation: false
---

# Dongchedi Charging Confluence Pipeline

## Purpose
执行懂车帝 charging 数据日常流水线，生成当日报告产物，并按需发布到 Confluence。默认执行完整流程（生成 + 发布），同时支持 dry-run 安全模式。

## When To Use
- 你希望一次触发懂车帝 charging 数据流程并更新 Confluence 页面。
- 你需要每天固定产出 `filtered.csv`、`filtered.json`、`summary.md`、`confluence_section.html`。
- 你要在发布前先验证数据质量，或只做本地 dry-run。

## Inputs
- `date` (optional): 指定跑数日期，格式 `YYYY-MM-DD`。
- `publish` (optional, default `true`): 是否发布到 Confluence。
- `refresh_source` (optional, default `false`): 是否实时刷新懂车帝源数据。
- `strict_refresh` (optional, default `false`): 刷新是否启用严格阈值。
- `no_backfill` (optional, default `true`): 避免自动补跑历史缺口。

## Prerequisites
- Python 虚拟环境存在: `.\\.venv\\Scripts\\python.exe`。
- Self-contained scripts exist under this skill folder: `.\\.github\\skills\\dongchedi-charging-confluence-pipeline\\scripts\\`.
- 可读取数据源文件: `dongchedi_full_configs_YYYY-MM-DD.csv`（或由现有流程可定位到最新文件）。
- 价格映射文件可用: `dongchedi_price_map.csv`。
- 若 `publish=true`，必须具备 Confluence 环境变量:
- `CONFLUENCE_BASE_URL`
- `CONFLUENCE_EMAIL`
- `CONFLUENCE_API_TOKEN`
- `CONFLUENCE_DAILY_PARENT_PAGE_ID` (preferred) or `CONFLUENCE_DAILY_PAGE_ID`
- `CONFLUENCE_MOTOR_PARENT_PAGE_ID` (optional compatibility key for shared Confluence setup)

Confluence page id resolution for this skill:
- Daily pipeline prioritizes `CONFLUENCE_DAILY_PARENT_PAGE_ID` or `CONFLUENCE_DAILY_PAGE_ID`.
- `CONFLUENCE_MOTOR_PARENT_PAGE_ID` is documented for cross-pipeline compatibility, but does not replace daily keys unless your script logic is extended.

## Procedure
1. 解析输入参数。若未提供参数，使用默认值:
- `publish=true`
- `refresh_source=false`
- `strict_refresh=false`
- `no_backfill=true`
2. 构建生成命令并执行:
- Base:
  - `.\\.venv\\Scripts\\python.exe .\\.github\\skills\\dongchedi-charging-confluence-pipeline\\scripts\\run_dongchedi_daily.py --no-backfill-missing`
- If `date` provided:
  - append `--date <date>`
- If `publish=false`:
  - append `--dry-run`
- If `refresh_source=true`:
  - append `--refresh-source`
- If `strict_refresh=true`:
  - append `--refresh-source-strict --refresh-source-min-success-rate 0.60 --refresh-source-min-successes 1`
3. 校验产物目录 `reports/dongchedi_daily/<resolved-date>/` 至少包含:
- `filtered.csv`
- `filtered.json`
- `summary.md`
- `confluence_section.html`
4. 若 `publish=true` 且生成成功，执行发布命令:
- `.\\.venv\\Scripts\\python.exe .\\.github\\skills\\dongchedi-charging-confluence-pipeline\\scripts\\push_dongchedi_to_confluence.py`
5. 汇总并返回结果（见 Output Contract）。

### Self-contained Quick Start
- Precheck: `.\\.venv\\Scripts\\python.exe .\\.github\\skills\\dongchedi-charging-confluence-pipeline\\scripts\\precheck_confluence_env.py --mode pipeline`
- Full run: `.\\.venv\\Scripts\\python.exe .\\.github\\skills\\dongchedi-charging-confluence-pipeline\\scripts\\run_dongchedi_daily.py --no-backfill-missing`
- Publish-only retry: `.\\.venv\\Scripts\\python.exe .\\.github\\skills\\dongchedi-charging-confluence-pipeline\\scripts\\push_dongchedi_to_confluence.py`

## Failure Handling
- Missing source CSV:
- 终止流程，提示补齐 `dongchedi_full_configs_YYYY-MM-DD.csv` 或指定 `date`。
- Missing `dongchedi_price_map.csv` or unresolved prices:
- 终止流程，提示补齐价格映射后重试。
- Generation failed:
- 不执行 Confluence 发布，返回失败摘要和最近日志路径。
- Publish failed:
- 保留已生成本地产物，返回 Confluence 错误信息和排查建议。
- Missing Confluence env with `publish=true`:
- 快速失败并明确缺失变量名。
- If only `CONFLUENCE_MOTOR_PARENT_PAGE_ID` is present:
- 视为配置不完整，提示补齐 `CONFLUENCE_DAILY_PARENT_PAGE_ID` 或 `CONFLUENCE_DAILY_PAGE_ID`。

## Output Contract
每次执行必须返回:
- Resolved date
- Executed command list
- Artifact directory
- Artifact existence check (pass/fail per file)
- Publish status (`skipped`/`success`/`failed`)
- Confluence page URL or page ID when available
- Next action when failed

## Safety Notes
- 当用户明确需要“只抓取不发布”时，必须设置 `publish=false`。
- 当用户未要求历史补跑时，保持 `no_backfill=true`。
- 仅在生成成功后发布，避免空白或不完整内容覆盖 Confluence 页面。

## Example Prompts
- `/dongchedi-charging-confluence-pipeline` today full run and publish.
- `/dongchedi-charging-confluence-pipeline date=2026-06-17 publish=false`.
- `/dongchedi-charging-confluence-pipeline date=2026-06-17 publish=true refresh_source=true strict_refresh=true`.
- `帮我跑懂车帝 charging 日报并更新 Confluence，日期用今天。`
- `先 dry-run 懂车帝 charging，再告诉我是否可以发布。`

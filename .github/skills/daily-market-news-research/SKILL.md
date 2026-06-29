---
name: daily-market-news-research
description: "Daily multi-market news research for US, China, Korea, and Hong Kong equities and themes such as semiconductors, AI compute, memory, gold, and precious metals. Includes runnable workflow entrypoints and task hooks for repeatable daily execution."
argument-hint: "可选参数: date=YYYY-MM-DD, mode=watchlist|theme|mixed, markets=us,cn,kr,hk, symbols=<comma-separated>, themes=<comma-separated>, max_items=10, language=zh|en|bilingual, dry_run=true|false, request_timeout=15, emit_json=<path>"
user-invocable: true
disable-model-invocation: false
---

# Daily Market News Research

## Purpose
把多市场每日新闻检索固化成可重复执行流程：围绕美国、中国、韩国、香港市场，按股票池或主题检索半导体、AI 算力、存储、黄金、贵金属等相关新闻，并输出可直接复制到 Feishu 或 Confluence 的双语 Markdown 简报。

## When To Use
- 你需要每天快速扫一遍多市场新闻，不想手工切换多个站点。
- 你希望同时支持固定股票池和行业主题两种检索方式。
- 你需要保留来源链接、标题和简短判断，便于后续跟踪。

## Inputs
- `date` (optional, default `today`): 报告日期。
- `mode` (optional, default `mixed`):
  - `watchlist`: 只按股票池检索。
  - `theme`: 只按主题检索。
  - `mixed`: 股票池 + 主题双模式。
- `markets` (optional, default `us cn kr hk`): 参与检索的市场范围。
- `symbols` (optional): 逗号分隔的关注标的，例如 `NVDA,TSM,000660.KS,0700.HK`。
- `themes` (optional): 逗号分隔的主题关键词，例如 `semiconductor,ai compute,memory,gold,precious metals`。
- `max_items` (optional, default `10`): 每个市场或主题最多保留的新闻条数。
- `language` (optional, default `bilingual`): `zh`、`en` 或 `bilingual`。
- `dry_run` (optional, default `true`): 是否只生成本地结果，不执行发布。
- `emit_json` (optional): 额外输出机器可读 JSON 路径，便于后续自动发布或二次处理。

## Ready-to-Copy Template Files
- `.github/skills/daily-market-news-research/templates/daily-market-news-research/scripts/run_daily_market_news_research.py`
- `.github/skills/daily-market-news-research/templates/daily-market-news-research/config/default_sources.json`
- `.github/skills/daily-market-news-research/templates/daily-market-news-research/README.md`

## Prerequisites
- Python 可执行文件可用：`./.venv/Scripts/python.exe`
- 可访问公开新闻源（默认使用 Google News RSS 搜索页）
- 若要调整默认覆盖范围：编辑模板配置里的市场、股票池和主题关键词

## Data Source Policy
- 优先公开网页来源，不依赖登录态或付费源。
- 默认启用并收紧为 3 类来源：
  - Google News RSS（市场本地化检索）
  - Yahoo Finance RSS（按 symbol 抓 headline）
  - 交易所公告（按市场映射站点过滤，US 额外接 SEC Atom feed）
- 后续若要扩展付费源，应通过新增配置，不改变现有输入语义。

## Procedure
1. 读取输入参数并解析目标日期、市场、股票池和主题。
2. 按 `mode` 选择检索路径：
   - `watchlist`: 逐个标的检索相关新闻。
   - `theme`: 按主题关键词检索相关新闻。
   - `mixed`: 两条路径都执行并合并去重。
3. 对每个结果保留标题、来源、发布时间、链接、相关市场或主题标签。
4. 按市场分组，再按主题汇总，去除重复标题与近似重复链接。
5. 生成双语 Markdown 报告，包含摘要、市场分段、主题分段、重点新闻和来源清单。
6. 若提供 `emit_json`，同步输出结构化 JSON，供后续自动化流水线使用。
7. 若 `dry_run=false` 且后续接入发布动作，则仅在本地校验通过后再执行。

## Daily Workflow Entry Points
- Repo-level script entry: `scripts/run_daily_market_news.py`
- Template implementation: `.github/skills/daily-market-news-research/templates/daily-market-news-research/scripts/run_daily_market_news_research.py`
- VS Code tasks:
  - `Daily Market News: Dry Run`
  - `Daily Market News: Run`

推荐先执行 Dry Run，再执行 Run（当前 Run 仍是本地落地报告，不会写外部系统）。

## Validation Checklist
- 报告日期已解析。
- 至少一个市场或主题命中结果。
- 每条重点新闻都有来源链接。
- 输出文件可写。
- 若提供 `emit_json`，JSON 结构可被后续脚本读取。

## Failure Handling
- No sources found:
  - 返回空结果摘要，并提示扩大股票池或放宽主题关键词。
- Source unavailable:
  - 跳过该来源并继续其余来源，记录失败项。
- Invalid mode or market:
  - 终止并提示允许值。
- Output write failure:
  - 终止并保留已采集结果，不执行任何发布动作。

## Output Contract
每次执行必须返回：
- Resolved date
- Mode, markets, symbols, themes
- 重点新闻列表（标题、来源、链接、市场或主题标签）
- 市场分组摘要
- 主题分组摘要
- 生成文件路径
- 可选 JSON 路径
- Validation result

## Safety Notes
- 默认只读，不修改外部系统。
- 默认先 dry run，再考虑发布或自动化集成。
- 不缓存或公开任何登录凭据。

## Example Prompts
- `/daily-market-news-research`
- `/daily-market-news-research date=2026-06-22 mode=mixed markets=us cn kr hk symbols=NVDA,TSM,000660.KS,0700.HK themes=semiconductor,ai compute,memory,gold language=bilingual dry_run=true`
- `请按 daily-market-news-research 流程给我今天的多市场新闻简报，重点看半导体、AI 算力、存储和黄金。`
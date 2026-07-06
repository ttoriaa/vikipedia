---
name: foundation-model-release-watch
description: "定期追踪国内外基座大模型新发布、版本更新与价格能力变化，输出结构化周报与变更清单。Use when you need periodic frontier model launch monitoring across OpenAI, Anthropic, Google, DeepSeek, Moonshot, GLM, Qwen and peers."
argument-hint: "可选参数: date=YYYY-MM-DD, cadence=daily|weekly, window_days=7, providers=openai,anthropic,google,deepseek,moonshot,glm,qwen,meta,mistral, max_items=5, language=zh|en|bilingual, dry_run=true|false, emit_json=<path>"
user-invocable: true
disable-model-invocation: false
---

# Foundation Model Release Watch

## Purpose
把基座大模型市场跟踪固化为可重复执行流程，定期扫描国内外主流厂商的新模型发布、版本更新、价格变化、能力边界与企业可用性，输出可直接用于周会和管理汇报的研究结果。

## When To Use
- 你需要每周固定更新一次国内外大模型动态，不想手工反复查官网和公告。
- 你要横向比较 OpenAI、Anthropic、Google、DeepSeek、Moonshot、GLM、Qwen 等厂商。
- 你需要一份包含新增模型、关键变化、风险提示、可落地建议的统一报告。

## Inputs
- date (optional, default today): 报告日期。
- cadence (optional, default weekly): 追踪频率，daily 或 weekly。
- window_days (optional, default 7): 回溯窗口天数。
- providers (optional): 逗号分隔厂商清单。
  - 默认: openai, anthropic, google, deepseek, moonshot, glm, qwen, meta, mistral
- max_items (optional, default 5): 每家厂商保留的重点更新数量。
- language (optional, default bilingual): zh 或 en 或 bilingual。
- dry_run (optional, default true): 默认只生成本地报告，不触发对外发布。
- emit_json (optional): 额外输出 JSON 路径，用于自动化二次处理。

## Coverage Baseline
- International: OpenAI, Anthropic, Google, Meta, Mistral
- China: DeepSeek, Moonshot, Zhipu GLM, Qwen
- 可按输入参数扩展更多厂商。

## Data Source Policy
- 优先官方一手来源：官方博客、发布页、API 文档、价格页、模型卡。
- 官方来源不足时，可补充高可信二手来源，并明确标记为二手。
- 每条结论必须可回溯到来源链接，不做无来源断言。

## Core Tracking Dimensions
1. Release and Version:
   - 新模型/新版本名称、发布时间、版本标识。
2. Capability Changes:
   - 模态能力、上下文窗口、推理能力、Agent 工具能力、代码能力。
3. Commercial Changes:
   - API 定价、套餐变化、免费额度、企业许可与地区可用性。
4. Enterprise Readiness:
   - 数据合规、私有化可选项、SLA、审计能力、接入复杂度。

## Procedure
1. 解析输入参数，确定报告日期、回溯窗口和厂商清单。
2. 为每个厂商建立检索矩阵：release notes、pricing、api docs、model cards、blog。
3. 采集窗口期内的更新，保留标题、日期、链接、摘要。
4. 提取结构化字段：
   - provider
   - model_or_version
   - release_date
   - change_type (new model or update or pricing or policy)
   - highlights
   - enterprise_impact
   - source_url
5. 生成差异对比：与上一期快照比对，标注新增、下线、降价、能力跃迁。
6. 输出 Markdown 报告和可选 JSON。
7. 若 dry_run=false，可进入你现有发布流程（Confluence 或 Feishu）。

## Automation Entry Points
- Repo script entry: `scripts/run_foundation_model_release_watch.py`
- Workflow: `.github/workflows/sync-foundation-model-release-watch.yml`
- Default schedule: every Monday morning Beijing time (cron `10 1 * * 1`, UTC)

推荐先手动 dry run 验证，再启用自动定时：
- `python scripts/run_foundation_model_release_watch.py --dry-run true`
- `python scripts/run_foundation_model_release_watch.py --cadence weekly --window-days 7 --providers openai,anthropic,google,deepseek,moonshot,glm,qwen --dry-run false`

## Output Contract
每次执行必须返回：
- Resolved date and window
- Providers covered and missing providers
- Top updates per provider
- Cross-provider comparison summary
- Enterprise impact summary
- Source list (one line per source)
- Output files (markdown and optional json)
- Validation result

## Report Template
- Section A: Executive Summary
- Section B: Provider-by-Provider Updates
- Section C: Cross-Vendor Comparison Table
- Section D: Enterprise Adoption Signals and Risks
- Section E: Next Watchlist for Upcoming Week

## Validation Checklist
- 每家厂商至少有 1 条可验证来源或被标记为 no update。
- 每条重点结论附来源链接。
- 至少输出 1 个跨厂商比较表。
- 结论与来源无冲突。

## Failure Handling
- Official source unavailable:
  - 记录失败并回退二手来源，标记置信度。
- Provider has no updates in window:
  - 明确输出 no update，不强行填充。
- Conflicting claims across sources:
  - 同时列出冲突信息，标记 pending verification。
- Output write failure:
  - 返回错误并提供建议路径重试。

## Safety Notes
- 禁止杜撰发布时间、参数规模、定价信息。
- 对未公开指标使用 unknown 或 not disclosed。
- 默认 dry_run=true，先校验后发布。

## Example Prompts
- /foundation-model-release-watch
- /foundation-model-release-watch cadence=weekly window_days=7 providers=openai,anthropic,google,deepseek,moonshot,glm,qwen language=bilingual dry_run=true
- 请按 foundation-model-release-watch 生成本周基座大模型更新简报，重点比较价格变化和企业可落地性。
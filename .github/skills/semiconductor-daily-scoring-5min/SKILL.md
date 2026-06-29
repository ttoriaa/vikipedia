---
name: semiconductor-daily-scoring-5min
description: "5分钟完成半导体公司日评打分：按公司类型自动加权（Fabless/Foundry/IDM/设备/封测），抓取 Yahoo + IR + 行业政策证据并输出 Markdown 日报。Use when you need fast, repeatable daily semiconductor scoring with explainable evidence."
argument-hint: "可选参数: date=YYYY-MM-DD, universe=core3|ai6|custom, companies=SYMBOL:SCOPE:TYPE,..., emit_json=<path>, dry_run=true|false, auto_commit=true|false, auto_push=true|false"
user-invocable: true
disable-model-invocation: false
---

# Semiconductor Daily Scoring (5-Min)

## Purpose
把“半导体公司日评”固化成可重复执行流程：
1. 自动识别公司类型并套用对应权重。
2. 优先填 12 因子中的关键 6 项（其余默认中性 0）。
3. 汇总 Yahoo + IR + 行业政策页面证据。
4. 输出可直接粘贴到 Confluence/Feishu 的 Markdown 日报。

## When To Use
- 你需要每天 5 分钟内完成半导体公司跟踪。
- 你希望不同公司类型用不同权重，不再“一把尺子”。
- 你需要“可解释”的打分（每行都有证据）。

## Inputs
- `date` (optional, default `today`): 报告日期。
- `universe` (optional, default `core3`):
  - `core3`: SK hynix / TSM / ASML
  - `ai6`: SK hynix / TSM / ASML / NVDA / MU / MRVL
  - `custom`: 由 `companies` 指定
- `companies` (optional): `SYMBOL:SCOPE:TYPE` 逗号分隔。
  - 例如: `000660.KS:sg:IDM,TSM:sg:Foundry,ASML:sg:Equipment`
- `emit_json` (optional): 机器可读 JSON 输出路径。
  - 例如: `reports/semiconductor_daily/latest.json`
- `dry_run` (optional, default `true`): 是否仅本地生成报告。
- `auto_commit` (optional, default `false`): 是否自动提交报告。
- `auto_push` (optional, default `false`): 是否自动推送（仅 `auto_commit=true` 时有效）。

## Ready-to-Copy Template Files
- `.github/skills/semiconductor-daily-scoring-5min/templates/semiconductor-scoring/scripts/run_daily_semiconductor_scoring.py`
- `.github/skills/semiconductor-daily-scoring-5min/templates/semiconductor-scoring/config/default_universe.json`
- `.github/skills/semiconductor-daily-scoring-5min/templates/semiconductor-scoring/.github/workflows/semiconductor-daily-scoring.yml`
- `.github/skills/semiconductor-daily-scoring-5min/templates/semiconductor-scoring/README.md`

## Scoring Model (12 Factors)
每项取值：`+1`（偏多）/ `0`（中性）/ `-1`（偏空）

1. 应用需求强度（Agent/机器人/自动驾驶）
2. 算力扩张强度（GPU/AI 集群）
3. 存储紧张度（HBM/高端存储）
4. 交付可行性（良率/认证/量产）
5. 先进封装约束（CoWoS/2.5D/3D/测试）
6. 基建配套（电力/液冷/机房）
7. 财务质量（毛利率/现金流/ROIC）
8. 周期位置（库存/ASP/补去库）
9. 资本效率（Capex 转化）
10. 客户集中度风险
11. 技术路线兑现（节点/代际）
12. 地缘与政策风险（出口管制/关税）

## Company-Type Weights (Total=100)
- Fabless: `[10,12,8,8,8,4,12,10,6,8,8,6]`
- Foundry: `[8,10,6,10,10,6,10,8,10,6,10,6]`
- IDM: `[8,8,10,10,8,4,10,12,10,8,8,4]`
- Equipment: `[6,8,4,8,6,4,14,12,10,10,10,8]`
- OSAT: `[7,8,6,10,14,4,10,10,8,8,9,6]`

## Score Formula
`TotalScore = sum(weight_i * signal_i)`，范围 `[-100, +100]`

阈值解释：
- `+35 ~ +100`: 强偏多
- `+15 ~ +34`: 偏多
- `-14 ~ +14`: 中性
- `-34 ~ -15`: 偏空
- `-100 ~ -35`: 强偏空

## Procedure
1. 读取配置和输入参数，确定公司池与公司类型。
2. 对每家公司抓取证据：
- Yahoo quote 页面（价格、涨跌幅、财务摘要）
- Yahoo news 页面（当日新闻标题）
- 可选 IR / 行业政策页（来自配置）
3. 自动填关键 6 项（1,2,3,4,5,12），其余默认 0。
- 规则增强：结合新闻正负关键词、涨跌阈值、公司类型差异（Fabless/Foundry/IDM/Equipment/OSAT）。
4. 计算加权总分，生成结论级别。
5. 输出 Markdown 报告到 `reports/semiconductor_daily/`。
6. 若提供 `emit_json`，额外输出 JSON 结构用于 Feishu/Confluence 自动发布。
7. 若 `auto_commit=true`，提交报告；若 `auto_push=true`，推送远端。

## Failure Handling
- 某个来源抓取失败：对应因子维持 `0`，并记录 `source_unavailable`。
- 公司类型缺失：默认按 `IDM` 处理并在报告注明。
- 输出目录不可写：返回错误并终止，不执行 git 操作。

## Output Contract
每次执行必须返回：
- 报告日期与公司列表
- 每家公司：类型、12 因子信号、总分、结论、证据链接
- 生成文件路径
- 可选 JSON 路径（`emit_json`）
- 提交/推送状态

## Validation
- 至少 3 家公司报告行完整。
- 每家公司至少有 1 条证据链接。
- 总分与因子信号可回算。

## Example Prompts
- `/semiconductor-daily-scoring-5min`
- `/semiconductor-daily-scoring-5min universe=ai6 dry_run=true`
- `/semiconductor-daily-scoring-5min companies=000660.KS:sg:IDM,TSM:sg:Foundry,ASML:sg:Equipment emit_json=reports/semiconductor_daily/latest.json auto_commit=true auto_push=false`

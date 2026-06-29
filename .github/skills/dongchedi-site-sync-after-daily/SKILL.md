---
name: dongchedi-site-sync-after-daily
description: "在懂车帝充电日报数据更新后，同步更新网站 data.html、dashboard 和 insights 趋势总结。Use when you need to refresh automotive-benchmarking pages after CSV and Confluence update."
argument-hint: "可选参数: date=YYYY-MM-DD, deploy=true|false, dispatch_workflow=true|false"
user-invocable: true
disable-model-invocation: false
---

# Dongchedi Site Sync After Daily

## Purpose
在你完成当日懂车帝充电数据更新后，自动重建网站数据页、可视化页面和趋势总结页面，并按需触发 GitHub Pages 部署，让线上站点尽快同步。

## When To Use
- 你已经完成当日 CSV 更新和 Confluence 更新，想同步网站。
- 你需要更新以下页面:
- data.html
- dashboard.html
- insights.html
- 你希望将最新日报目录同步到 site/reports/<date>/ 并更新 site/latest 别名。

## Inputs
- date (optional): 报告日期，格式 YYYY-MM-DD。默认使用 reports/dongchedi_daily 下最新日期。
- deploy (optional, default true): 是否执行发布动作（推送后触发 Pages）。
- dispatch_workflow (optional, default true): 是否尝试触发 .github/workflows/dongchedi-pages.yml 的 workflow_dispatch。

## Prerequisites
- Python 可执行文件可用: ./.venv/Scripts/python.exe
- Self-contained scripts exist under this skill folder: ./.github/skills/dongchedi-site-sync-after-daily/scripts/
- 当日报告目录存在: reports/dongchedi_daily/<date>/
- 最少文件存在:
- filtered.csv
- summary.md
- 若要生成可视化页面，还需 charging_visualization_dashboard.html；如果缺失，先运行本 skill 的 Step 2 自动生成。
- 若要自动触发 workflow_dispatch，需 gh CLI 已安装并完成认证（gh auth login）。

## Procedure
1. 确认目标日期与输入目录。
2. 生成可视化 Dashboard 文件:
- ./.venv/Scripts/python.exe ./.github/skills/dongchedi-site-sync-after-daily/scripts/build_charging_visualizations.py --date <date>
3. 组装站点页面与归档:
- ./.venv/Scripts/python.exe ./.github/skills/dongchedi-site-sync-after-daily/scripts/build_dongchedi_pages_site.py
4. 同步 landing 为站点入口（与现有 CI 一致）:
- Copy-Item ./index.html ./site/index.html -Force
5. 验证关键输出:
- site/data.html
- site/dashboard.html
- site/insights.html
- site/reports/<date>/charging_visualization_dashboard.html
- site/latest/charging_visualization_dashboard.html
6. 若 deploy=true，执行代码提交与推送（仅提交 site/ 以及必要页面改动）。
7. 若 dispatch_workflow=true，尝试触发:
- gh workflow run .github/workflows/dongchedi-pages.yml
- 若 gh 不可用，返回手动触发指引。

## Self-contained Quick Start
- Local run (no deploy):
- powershell -NoProfile -ExecutionPolicy Bypass -File .\\.github\\skills\\dongchedi-site-sync-after-daily\\scripts\\sync_dongchedi_site_after_daily.ps1 -Deploy false -DispatchWorkflow false
- Run for specific date:
- powershell -NoProfile -ExecutionPolicy Bypass -File .\\.github\\skills\\dongchedi-site-sync-after-daily\\scripts\\sync_dongchedi_site_after_daily.ps1 -Date <YYYY-MM-DD> -Deploy false -DispatchWorkflow false

## Failure Handling
- Missing daily report directory:
- 终止并提示先执行日报 skill（dongchedi-charging-confluence-pipeline）。
- Missing filtered.csv:
- 终止并提示先完成 run_dongchedi_daily.py 生成。
- Visualization build failed:
- 终止并返回 build_charging_visualizations.py 错误摘要。
- Site assembly failed:
- 终止并返回 build_dongchedi_pages_site.py 错误摘要。
- Workflow dispatch failed:
- 保留本地 site 结果，返回 gh 登录或手动 Actions 触发路径。

## Output Contract
每次执行必须返回:
- Resolved date
- Executed command list
- Site files check result (pass or fail)
- Deploy status (skipped or success or failed)
- Workflow dispatch status (skipped or success or failed)
- Next action when failed

## Safety Notes
- 在 deploy=true 前先完成本地输出校验，避免发布损坏页面。
- 若只需本地预览，将 deploy=false。
- 若仅需触发线上重建而不改本地文件，可直接 dispatch_workflow=true 并跳过提交。

## Example Prompts
- /dongchedi-site-sync-after-daily date=2026-06-17
- /dongchedi-site-sync-after-daily date=2026-06-17 deploy=false
- /dongchedi-site-sync-after-daily date=2026-06-17 deploy=true dispatch_workflow=true
- 帮我把今天懂车帝充电日报同步到网站，包括数据页、可视化和趋势总结。

## 参数示例输入 -> 标准输出样例

可直接复制的参数输入（本地预览，不发布）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.github\skills\dongchedi-site-sync-after-daily\scripts\sync_dongchedi_site_after_daily.ps1 -Date 2026-06-29 -Deploy false -DispatchWorkflow false
```

可直接复制的参数输入（发布但不触发 workflow_dispatch）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.github\skills\dongchedi-site-sync-after-daily\scripts\sync_dongchedi_site_after_daily.ps1 -Date 2026-06-29 -Deploy true -DispatchWorkflow false
```

标准输出样例（终端）：

```text
Resolved date: 2026-06-29
Site files check: pass
Deploy status: skipped
Workflow dispatch status: skipped
```

标准输出样例（关键文件检查）：

```text
site/data.html
site/dashboard.html
site/insights.html
site/reports/2026-06-29/charging_visualization_dashboard.html
site/latest/charging_visualization_dashboard.html
```

# EV Benchmark Daily Publisher

## Purpose
将当日 EV Charging Benchmarking 报告从当前工作仓库同步到 automotive-benchmarking，并通过最小提交触发远端 GitHub Pages 构建，最终校验线上页面是否命中目标日期。

## When To Use
- 你已经在当前仓库产出 `reports/dongchedi_daily/<date>/`。
- 你希望将该日期数据发布到 `https://ttoriaa.github.io/automotive-benchmarking/`。
- 你需要一个可重复、可审计、最小改动的跨仓库发布流程。

## Inputs
- `date` (optional): 目标日期，格式 `YYYY-MM-DD`，默认今天。
- `source_repo` (optional): 源仓库路径，默认当前仓库根目录。
- `target_repo` (optional): 目标仓库路径，默认 `<source_repo>/../automotive-benchmarking`。
- `verify_live` (optional, default `true`): 推送后是否校验线上页面。
- `max_wait_seconds` (optional, default `900`): 线上校验等待时长。
- `poll_interval_seconds` (optional, default `20`): 校验轮询间隔。

## Prerequisites
- `source_repo/reports/dongchedi_daily/<date>/` 存在，并至少包含：
  - `filtered.csv`
  - `filtered.json`
  - `summary.md`
- 目标仓库可访问且有 push 权限。
- 本机可执行 `git`。

## Procedure
1. 解析日期与仓库路径，做前置校验。
2. 将 `source_repo/reports/dongchedi_daily/<date>/` 复制到 `target_repo/reports/dongchedi_daily/<date>/`。
3. 仅暂存 `target_repo/reports/dongchedi_daily/<date>/`（最小提交范围）。
4. 若有变更则 commit + push 到 `main`。
5. 若 `verify_live=true`，轮询以下页面是否包含目标日期：
   - `data.html`
   - `dashboard.html`
   - `insights.html`
6. 输出结构化结果（见 Output Contract）。

## Self-contained Quick Start
- 仅同步并推送（含线上校验）：
  - `.\\.venv\\Scripts\\python.exe .\\.github\\skills\\ev-benchmark-daily-publisher\\scripts\\publish_ev_benchmark_daily.py --date 2026-07-09`
- 不做线上校验：
  - `.\\.venv\\Scripts\\python.exe .\\.github\\skills\\ev-benchmark-daily-publisher\\scripts\\publish_ev_benchmark_daily.py --date 2026-07-09 --verify-live false`

## Output Contract
每次执行必须返回：
- `date`
- `source_repo`
- `target_repo`
- `copied_files`
- `commit_created` (true/false)
- `commit_sha` (if any)
- `push_status` (`success`/`failed`/`skipped`)
- `live_check`（每个页面是否命中目标日期）
- `final_status` (`success`/`failed`)
- `next_action`（失败时）

## Failure Handling
- Source date folder missing:
  - 直接失败并提示先跑日报。
- Git commit/push failed:
  - 返回命令错误与下一步建议，不修改其它路径。
- Live verification timeout:
  - 标记 `push success but deploy pending`，建议继续轮询或查看 Actions。

## Safety Notes
- 永远只提交 `reports/dongchedi_daily/<date>/`，避免带入无关改动。
- 若工作区有其它脏改动，发布流程仍应保持最小提交范围。
- 不使用 destructive git 命令。

# EV Benchmark Deploy Watchdog

## Purpose
巡检 EV Charging Benchmarking 线上页面是否命中目标日期；若落后可自动触发发布 skill，实现“检测 -> 修复 -> 复检”的闭环。

## When To Use
- 你希望每天自动确认 `automotive-benchmarking` 是否更新到当天数据。
- 你希望在发现落后时自动调用发布脚本补救。
- 你需要输出一份可审计的巡检结果。

## Inputs
- `date` (optional): 目标日期，默认今天。
- `auto_remediate` (optional, default `false`): 是否自动补救。
- `max_remediation_attempts` (optional, default `2`): 自动补救次数上限。
- `publisher_script` (optional): 发布脚本路径。
- `max_wait_seconds` (optional, default `900`): 每轮复检等待时长。

## Prerequisites
- 可访问目标页面：
  - `https://ttoriaa.github.io/automotive-benchmarking/data.html`
  - `https://ttoriaa.github.io/automotive-benchmarking/dashboard.html`
  - `https://ttoriaa.github.io/automotive-benchmarking/insights.html`
- 若 `auto_remediate=true`：必须可执行 publisher 脚本，并具备目标仓库 push 权限。

## Procedure
1. 检查三页是否命中目标日期。
2. 若都命中：直接成功返回。
3. 若未命中且 `auto_remediate=true`：调用 `publish_ev_benchmark_daily.py`。
4. 重新校验三页命中结果。
5. 在达到成功或尝试次数上限后输出最终结果。

## Self-contained Quick Start
- 只巡检：
  - `.\\.venv\\Scripts\\python.exe .\\.github\\skills\\ev-benchmark-deploy-watchdog\\scripts\\watch_ev_benchmark_deploy.py --date 2026-07-09`
- 巡检 + 自动补救：
  - `.\\.venv\\Scripts\\python.exe .\\.github\\skills\\ev-benchmark-deploy-watchdog\\scripts\\watch_ev_benchmark_deploy.py --date 2026-07-09 --auto-remediate true`

## Output Contract
每次执行必须返回：
- `date`
- `initial_check`（三页命中情况）
- `attempts`
- `remediation_runs`（每次发布返回码）
- `final_check`
- `final_status`
- `next_action`

## Failure Handling
- 站点访问失败：返回网络错误，标记为失败。
- 自动补救失败：返回 publisher 脚本退出码与最后错误。
- 超过最大尝试次数仍未命中：返回人工排查建议。

## Safety Notes
- 默认不自动写仓库（`auto_remediate=false`）。
- 自动补救时仅调用 publisher，不在 watchdog 中直接做 git 写操作。

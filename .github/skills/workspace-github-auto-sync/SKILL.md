---
name: workspace-github-auto-sync
description: "同步本地 workspace 到 GitHub 目标仓库，并在有更新时自动提交，按策略决定是否推送。Use when you need local->GitHub code sync for ttoriaa/viki-depot with auditable safeguards."
argument-hint: "推荐参数: repo_root=., expected_repo=ttoriaa/viki-depot, branch=main, mode=manual|scheduler, allow_push=true|false, dry_run=true|false"
user-invocable: true
disable-model-invocation: false
---

# Workspace GitHub Auto Sync

## Purpose
在本地工作区与 GitHub 仓库之间提供可重复执行的单向同步流程（local -> remote），自动识别改动、生成提交，并基于安全策略控制是否推送。

## When To Use
- 你希望把本地 workspace 改动同步到 `ttoriaa/viki-depot`。
- 你需要每日定时自动执行并保留可审计日志。
- 你希望在远端领先或分叉时自动停止，而不是自动重写历史。

## Inputs
- `repo_root` (optional, default `.`): 本地 git 仓库路径。
- `expected_repo` (optional, default `ttoriaa/viki-depot`): 期望的远端 `owner/repo`。
- `branch` (optional, default `main`): 目标分支。
- `mode` (optional, `manual|scheduler`, default `manual`): 执行模式。
- `allow_push` (optional, default `false`): 是否允许推送。
- `dry_run` (optional, default `false`): 只检测不写入。
- `commit_message` (optional): 自定义提交信息。

## Prerequisites
- 本地仓库可访问且 `git` 已安装。
- 目标仓库远端 `origin` 指向 `ttoriaa/viki-depot`。
- 当前分支为目标分支（默认 `main`）。
- 已配置本机 Git Credential Manager 鉴权。
- Python 可执行文件可用：`./.venv/Scripts/python.exe`。

## Procedure
1. 校验仓库根目录与 `origin` 目标仓库是否匹配。
2. `git fetch origin <branch>` 获取远端状态。
3. 比较 ahead/behind：
- 若远端领先（behind > 0）或分叉，立即停止并输出修复建议。
4. 统计本地改动（tracked + untracked，排除 ignored）。
5. 若无改动，返回 no-op。
6. 若 `dry_run=true`，只输出检测结果并停止。
7. `git add -A` 自动暂存本次改动。
8. 生成提交：默认 `chore(sync): workspace update YYYY-MM-DD HH:mm`。
9. 若 `allow_push=false`，返回 `pending-approval`。
10. 若 `allow_push=true`，执行带 OneDrive 保护参数的 push：
- `git -c gc.auto=0 -c maintenance.auto=false push origin <branch>`
11. push 后再次校验 ahead/behind，确认同步完成。

## Validation Checklist
- `repo_validation = ok`
- `remote_validation = ok`
- `behind = 0`
- `commit_status in {success, skipped}`
- 当 `allow_push=true` 时，`push_status in {success, failed, failed-verification}`

## Failure Handling
- Remote mismatch:
- 修复 `origin` 或通过 `expected_repo` 指定匹配值。
- Remote ahead/diverged:
- 停止执行，并提示先手动 `git pull --ff-only` 或手工解决。
- Commit failed:
- 返回 git 错误摘要，不执行 push。
- Push failed:
- 返回错误摘要和手工重试命令。

## Output Contract
每次执行至少返回：
- `repo_root`
- `expected_repo`
- `branch`
- `ahead` / `behind`
- `changed_files`
- `commit_status`
- `push_status`
- `next_action`
- `summary`

## Safety Notes
- 默认 `allow_push=false`，先提交后审批推送。
- 不执行 `force push`。
- 不自动执行 `pull --rebase` 或自动冲突解决。
- 仅处理当前仓库，不回滚无关文件。

## Local Scripts
- `scripts/sync_workspace_to_github.py`
- `scripts/run_workspace_github_sync_task_runner.ps1`
- `scripts/register_workspace_github_sync_task.ps1`

## Example Prompts
- `/workspace-github-auto-sync repo_root=. expected_repo=ttoriaa/viki-depot branch=main mode=manual dry_run=true`
- `/workspace-github-auto-sync repo_root=. expected_repo=ttoriaa/viki-depot branch=main mode=manual allow_push=false`
- `/workspace-github-auto-sync repo_root=. expected_repo=ttoriaa/viki-depot branch=main mode=manual allow_push=true`
- `帮我按 workspace-github-auto-sync 跑一次手动同步，先 commit 不 push。`

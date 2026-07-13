---
name: vikipediai-right-buttons-sync
description: "在 ttoriaa/VikipediAi 中定期刷新右侧按钮（Top Tabs）入口，避免手工维护和站点间数据源混淆。Use when you need scheduled right-button sync for the VikipediAi homepage."
argument-hint: "推荐发布模式: target_repo=ttoriaa/VikipediAi, username=ttoriaa, limit=6, auto_commit=true, auto_push=true；可选参数: source_feed_url=https://ttoriaa.github.io/vikipedia/assets/github-projects.json, include_names=vikipedia,VikipediAi, install_workflow=true"
user-invocable: true
disable-model-invocation: false
---

# VikipediAi Right Buttons Sync

## Purpose
在 `ttoriaa/VikipediAi` 仓库中固化一条可重复执行的同步流程，专门针对首页右侧按钮（Top Tabs / 右上按钮组）：
1. 从指定数据源读取候选站点（默认来自 `ttoriaa/vikipedia` 的 projects feed）。
2. 生成或更新 VikipediAi 使用的按钮配置文件（建议 `assets/right-buttons.json`）。
3. 确保 `index.html` 的按钮区优先读取该配置，而不是长期静态写死。
4. 安装并启用定时 GitHub Actions，使按钮入口自动刷新。

## Scope
本 skill 只面向 `VikipediAi` 站点右侧按钮，不处理 `vikipedia` 的 `#sites` 卡片区。

注意：
- `vikipedia` 和 `VikipediAi` 是两个不同站点，数据源与部署链路可独立。
- 当用户反馈“下面卡片有了，但右侧按钮没有”，优先检查是否仍在使用静态按钮列表。

## When To Use
- 你在 `VikipediAi` 页面右侧按钮里看不到新入口，但站点卡片区已经更新。
- 你希望右侧按钮按日/按小时自动同步，而不是每次改 `index.html`。
- 你需要一个可复用的“按钮数据化 + 定时刷新”流程。

## Inputs
- `target_repo` (optional, default `ttoriaa/VikipediAi`): 目标仓库。
- `username` (optional, default `ttoriaa`): GitHub 用户名。
- `source_feed_url` (optional, default `https://ttoriaa.github.io/vikipedia/assets/github-projects.json`): 按钮候选数据源。
- `limit` (optional, default `6`): 右侧按钮最多展示数量。
- `include_names` (optional): 强制保留的入口名，逗号分隔，如 `vikipedia,VikipediAi`。
- `output` (optional, default `assets/right-buttons.json`): 按钮配置输出路径。
- `auto_commit` (optional, recommended `true`): 自动提交。
- `auto_push` (optional, recommended `true`): 自动推送。
- `install_workflow` (optional, default `true`): 缺少自动化时安装 workflow。

推荐发布组合：
- `auto_commit=true auto_push=true install_workflow=true`

默认执行倾向：
- 未明确要求 dry-run 时，优先按发布模式执行。

## Existing Implementation Surface
若目标仓库尚未具备按钮数据化能力，建议新增：
- `scripts/sync_right_buttons.py`
- `.github/workflows/sync-right-buttons.yml`
- `assets/right-buttons.json`
- `index.html` 中读取 `assets/right-buttons.json` 的按钮渲染逻辑

## Procedure
1. 确认当前操作仓库是 `ttoriaa/VikipediAi`。
2. 检查 `index.html` 的右侧按钮是否仍为静态 hardcode。
3. 若尚未数据化：
- 添加 `assets/right-buttons.json` 与前端渲染逻辑。
- 将静态按钮作为 fallback，避免首次加载失败。
4. 运行同步脚本（示例）：
- `python scripts/sync_right_buttons.py --username <username> --source-feed-url <source_feed_url> --output <output> --limit <limit>`
- 若有 `include_names`，追加 `--include-names <csv>`。
5. 校验输出文件可解析且按钮条目非空。
6. 若 `auto_commit=true`：
- `git add <output> index.html .github/workflows/sync-right-buttons.yml scripts/sync_right_buttons.py`
- 仅在 staged 非空时提交：`git commit -m "chore: sync VikipediAi right buttons"`
7. 若 `auto_push=true`：
- `git push`
8. 启用 `.github/workflows/sync-right-buttons.yml` 的 `schedule + workflow_dispatch`。

## Validation
执行后至少验证：
- `assets/right-buttons.json` 可解析。
- `https://ttoriaa.github.io/VikipediAi/index.html` 右侧按钮出现目标入口。
- workflow 在无变更时不产生空 commit。

## Failure Handling
- 线上按钮未更新：
- 优先检查 `VikipediAi` 自身的 Pages workflow 是否成功，而不是 `vikipedia` 的部署状态。
- 数据源正常但按钮缺失：
- 检查 `index.html` 是否读取了 `assets/right-buttons.json`，或仍在使用静态按钮数组。
- workflow 失败：
- 先查看 Deploy 步骤是否为平台瞬时错误；必要时触发新的 workflow_dispatch（不要反复 re-run 同一 run）。

## Output Contract
每次执行应返回：
- Target repo
- Source feed URL
- Output path
- Synced button count
- Commit status (`skipped` / `success` / `failed`)
- Push status (`skipped` / `success` / `failed`)
- Next action when failed

## Example Prompts
- `/vikipediai-right-buttons-sync target_repo=ttoriaa/VikipediAi username=ttoriaa limit=6 auto_commit=true auto_push=true install_workflow=true`
- `/vikipediai-right-buttons-sync source_feed_url=https://ttoriaa.github.io/vikipedia/assets/github-projects.json include_names=vikipedia,VikipediAi auto_commit=true auto_push=true`
- `帮我把 VikipediAi 右侧按钮改成可定时同步，不要再手工写死。`

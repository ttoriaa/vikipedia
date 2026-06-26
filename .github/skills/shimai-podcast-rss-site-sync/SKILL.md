---
name: shimai-podcast-rss-site-sync
description: "在 shimai-podcast-site 中检测 RSS 是否更新；若有更新则刷新站点数据并按需提交推送。Use when you need podcast site data refresh only when RSS feed changes."
argument-hint: "可选参数: rss_url=<url>, update_command=<cmd>, changed_paths=<path1,path2>, auto_commit=true|false, auto_push=true|false"
user-invocable: true
disable-model-invocation: false
---

# Shimai Podcast RSS Site Sync

## Purpose
在 podcast 网站仓库内实现一个可重复执行的“增量同步”流程：
1. 拉取 RSS。
2. 计算 feed 指纹并与上次状态比对。
3. 仅当 RSS 发生变化时执行站点数据更新命令。
4. 按需提交并推送更新后的站点文件。

## When To Use
- 你希望避免每次都全量重建网站。
- 你需要一个可被 Copilot 反复调用的固定流程。
- 你想在 GitHub Actions / 定时任务中安全复用相同逻辑。

## Inputs
- `rss_url` (required): RSS 地址。
- `update_command` (optional): 站点数据更新命令。
  - 例如: `npm run update:data`
  - 或: `python scripts/update_site_from_rss.py`
- `changed_paths` (optional, default `public/data`): 逗号分隔的输出路径列表（文件或目录）。
- `auto_commit` (optional, default `false`): 是否自动提交。
- `auto_push` (optional, default `false`): 是否自动推送（仅在 `auto_commit=true` 时有效）。

## Ready-to-Copy Template Files
- `.github/skills/shimai-podcast-rss-site-sync/templates/shimai-podcast-site/scripts/rss-sync.mjs`
- `.github/skills/shimai-podcast-rss-site-sync/templates/shimai-podcast-site/.github/workflows/rss-site-sync.yml`
- `.github/skills/shimai-podcast-rss-site-sync/templates/shimai-podcast-site/README.md`

## Prerequisites
- 仓库已能通过命令行更新 RSS 到站点数据（`update_command` 可运行）。
- 工作目录是 `ttoriaa/shimai-podcast-site` 根目录。
- 若需要自动推送，`git` 远端权限可用。

## State File
将 RSS 状态落盘到固定文件，避免重复更新。建议路径:
- `.cache/rss_state.json`

推荐结构:
```json
{
  "rss_url": "https://example.com/feed.xml",
  "etag": "W/\"abc123\"",
  "last_modified": "Tue, 16 Jun 2026 12:00:00 GMT",
  "content_sha256": "...",
  "checked_at": "2026-06-17T08:00:00Z"
}
```

## Procedure
1. 读取输入参数，确定 `rss_url`、`update_command`、`changed_paths`。
2. 使用 `If-None-Match` / `If-Modified-Since` 请求 RSS。
3. 判定是否更新:
- HTTP `304` -> 视为未更新，直接结束。
- HTTP `200` -> 计算 `content_sha256` 并与状态文件比对。
- 若 hash 未变化 -> 结束。
- 若 hash 变化 -> 执行 Step 4。
4. 执行站点更新命令 `update_command`。
5. 验证关键输出是否更新（检查 `changed_paths` 中路径存在且非空）。
6. 更新 `.cache/rss_state.json`。
7. 若 `auto_commit=true`:
- `git add <changed_paths> .cache/rss_state.json`
- `git commit -m "chore: sync podcast data from RSS"`
8. 若 `auto_push=true`:
- `git push`

## Failure Handling
- RSS 请求失败:
- 返回 HTTP 状态码和错误摘要，不执行更新命令。
- `update_cmd` 失败:
- 不更新状态文件，返回失败日志摘要。
- 输出校验失败:
- 不提交，返回缺失文件列表。
- Git push 失败:
- 保留本地 commit，返回远端错误信息。

## Output Contract
每次执行必须返回:
- RSS check result (`changed`/`not_changed`/`failed`)
- HTTP status (`200`/`304`/...)
- Executed update command
- Changed files summary
- Commit status (`skipped`/`success`/`failed`)
- Push status (`skipped`/`success`/`failed`)
- Next action when failed

## GitHub Actions Integration (Recommended)
可在 `.github/workflows/rss-site-sync.yml` 使用定时触发 + 手动触发:

```yaml
name: RSS Site Sync

on:
  schedule:
    - cron: "*/30 * * * *"
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm ci
      - name: Sync from RSS when changed
        run: |
          # Replace with your real script/command
          npm run rss:sync
      - name: Commit if changed
        run: |
          if [ -n "$(git status --porcelain)" ]; then
            git config user.name "github-actions[bot]"
            git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
            git add -A
            git commit -m "chore: auto sync podcast site data"
            git push
          fi
```

## Example Prompts
- `/shimai-podcast-rss-site-sync rss_url=https://example.com/feed.xml update_command="npm run update:data" changed_paths=public/data auto_commit=true auto_push=true`
- `/shimai-podcast-rss-site-sync rss_url=https://example.com/feed.xml update_command="python scripts/update_site_from_rss.py" auto_commit=false`
- `检查 RSS 是否有更新；如果有就更新站点数据，但先不要 push。`

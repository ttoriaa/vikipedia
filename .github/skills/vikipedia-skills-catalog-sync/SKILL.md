---
name: vikipedia-skills-catalog-sync
description: "同步当前 workspace 的 .github/skills 到 Vikipedia landing page skills 区块数据源。Use when you need to refresh assets/skills-catalog.json from local skills and optionally auto commit/push."
argument-hint: "推荐参数: repo_root=., repo_slug=ttoriaa/vikipedia, output=assets/skills-catalog.json, mirror_site=true, auto_commit=true, auto_push=true"
user-invocable: true
disable-model-invocation: false
---

# Vikipedia Skills Catalog Sync

## Purpose
把当前 workspace 下 `.github/skills` 的最新状态同步到 Vikipedia 首页 Skills 区块使用的数据源 `assets/skills-catalog.json`，让首页展示的 skill 列表始终和本地 workspace 保持一致，并可按需自动提交和推送。

## When To Use
- 你新增、删除或更新了某个 skill，希望 Vikipedia 首页 Skills 区块立即反映。
- 你希望一次命令完成：生成 catalog -> 可选镜像到 `site/assets` -> 可选 commit/push。
- 你希望在本地和线上展示的数据保持一致。
- 你希望首页 `Skills` 区块自动刷新，而不是手工维护 skill 卡片或索引。
- 你希望 `index.html` 和 `site/index.html` 读取到的 skills 数据保持同步。

## Inputs
- `repo_root` (optional, default `.`): 目标仓库根目录。
- `repo_slug` (optional, default `ttoriaa/vikipedia`): GitHub 仓库标识。
- `output` (optional, default `assets/skills-catalog.json`): skills catalog 输出路径。
- `mirror_site` (optional, default `false`): 是否同步复制到 `site/assets/skills-catalog.json`。
- `branch` (optional, default `main`): 推送分支。
- `auto_commit` (optional, default `false`): 是否自动提交变更。
- `auto_push` (optional, default `false`): 是否在提交后自动推送。
- `commit_message` (optional): 自定义提交信息。

## Existing Implementation Surface
- `scripts/build_skills_catalog.py`
- `scripts/sync_vikipedia_skills_catalog.py`
- `index.html` and `site/index.html` load `assets/skills-catalog.json`
- `site/assets/skills-catalog.json` mirrors the same catalog for the published site.

## Procedure
1. 在目标仓库根目录运行同步脚本，生成最新 skills catalog。
2. 若 `mirror_site=true`，把生成文件复制到 `site/assets/skills-catalog.json`。
3. 若 `auto_commit=true`，仅提交 catalog 相关文件。
4. 若 `auto_push=true`，推送到 `origin/<branch>`。

## Validation
- `assets/skills-catalog.json` 可成功解析。
- 首页 `Skills` 区块能加载最新 skill 清单，且本地与线上站点展示一致。
- 当无变更时，脚本返回 `commit_status=skipped`，不会制造空提交。

## Failure Handling
- 找不到 `scripts/build_skills_catalog.py`：停止并返回缺失路径。
- `--auto-push` 未开启 `--auto-commit`：立即失败并提示参数组合无效。
- `git add/commit/push` 失败：返回失败状态与错误输出，便于重试。

## Output Contract
每次执行返回 JSON，至少包含：
- `repo_root`
- `repo_slug`
- `output`
- `generated`
- `changed_files`
- `commit_status`
- `commit_hash`
- `push_status`
- `summary`

## Command Examples
- 仅本地刷新:
  - `./.venv/Scripts/python.exe ./scripts/sync_vikipedia_skills_catalog.py --repo-root . --repo-slug ttoriaa/vikipedia`
- 刷新并同步到 site 目录:
  - `./.venv/Scripts/python.exe ./scripts/sync_vikipedia_skills_catalog.py --repo-root . --repo-slug ttoriaa/vikipedia --mirror-site`
- 刷新并自动提交推送:
  - `./.venv/Scripts/python.exe ./scripts/sync_vikipedia_skills_catalog.py --repo-root . --repo-slug ttoriaa/vikipedia --mirror-site --auto-commit --auto-push --branch main`

## Example Prompts
- `/vikipedia-skills-catalog-sync repo_root=. repo_slug=ttoriaa/vikipedia`
- `/vikipedia-skills-catalog-sync repo_root=. repo_slug=ttoriaa/vikipedia mirror_site=true auto_commit=true auto_push=true`
- `把当前 workspace 的 skills 同步到 Vikipedia 首页并推送到 main。`

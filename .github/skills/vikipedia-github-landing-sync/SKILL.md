---
name: vikipedia-github-landing-sync
description: "在 ttoriaa/vikipedia 中检测 GitHub 新建仓库或新公开项目站点，并定期更新 landing page 的 sites 数据源。Use when you need to refresh Vikipedia landing page from GitHub repositories on a schedule or on demand."
argument-hint: "可选参数: username=ttoriaa, limit=9, output=assets/github-projects.json, include_homepage_any_domain=false, auto_commit=true|false, auto_push=true|false, install_workflow=true|false"
user-invocable: true
disable-model-invocation: false
---

# Vikipedia GitHub Landing Sync

## Purpose
在 `ttoriaa/vikipedia` 仓库中固化一条可重复执行的同步流程：
1. 从 GitHub API 拉取指定用户的公开 repositories。
2. 识别适合展示到 landing page `#sites` 区块的项目。
3. 生成或更新 `assets/github-projects.json`。
4. 按需安装/复用 GitHub Actions 定时任务，使 landing page 自动刷新。

## Scope
默认检测两类 repository：
- 开启了 GitHub Pages 的仓库。
- 配置了 homepage 的仓库。

可选地也检测：
- 公开的 GitHub Projects V2 看板。

注意：
- 这里的 “项目” 包含可公开展示的 repository/project site，也可以包含 GitHub Projects 看板。
- GitHub Projects V2 通过 GraphQL 查询，通常需要可用 token。

## When To Use
- 你新建了 GitHub Pages 项目，希望它自动出现在 `Vikipedia: Let's roll.` 的 `#sites` 区块。
- 你希望 landing page 定时检查 GitHub 是否新增可展示项目，而不是手动维护卡片。
- 你想在目标仓库里快速落地脚本 + workflow，而不是每次手工拼装。

## Inputs
- `username` (optional, default `ttoriaa`): GitHub 用户名。
- `limit` (optional, default `9`): landing page 最多展示多少个项目。
- `output` (optional, default `assets/github-projects.json`): 数据输出路径。
- `include_homepage_any_domain` (optional, default `false`):
  - `false`: 仅收录 GitHub Pages 项目或指向 GitHub Pages 的 homepage。
  - `true`: 也收录任何配置了 homepage 的仓库。
- `include_project_boards` (optional, default `true` in workflow / `false` in bare CLI unless env is set): 是否收录公开 GitHub Projects V2 看板。
- `project_board_limit` (optional, default `20`): 预抓取多少个看板，再与仓库混排后截断。
- `auto_commit` (optional, default `false`): 是否自动提交 JSON 更新。
- `auto_push` (optional, default `false`): 是否自动推送远端。
- `install_workflow` (optional, default `false`): 若目标仓库缺少自动化，是否安装模板 workflow 与脚本。

## Existing Implementation Surface
当前仓库已有可直接复用的实现：
- `scripts/sync_github_projects.py`
- `.github/workflows/sync-github-projects.yml`
- `index.html` 中对 `assets/github-projects.json` 的加载逻辑

## Ready-to-Copy Template Files
- `.github/skills/vikipedia-github-landing-sync/templates/vikipedia/scripts/sync_github_projects.py`
- `.github/skills/vikipedia-github-landing-sync/templates/vikipedia/.github/workflows/sync-github-projects.yml`
- `.github/skills/vikipedia-github-landing-sync/templates/vikipedia/README.md`

## Preconditions
- 工作目录为目标 landing page 仓库根目录，例如 `ttoriaa/vikipedia`。
- landing page 已通过前端代码加载 `assets/github-projects.json`。
- 若使用 GitHub Actions 自动推送，仓库需允许 `GITHUB_TOKEN` 写入内容。

## Procedure
1. 确认目标仓库是否已存在 `scripts/sync_github_projects.py` 与 `.github/workflows/sync-github-projects.yml`。
2. 若不存在且 `install_workflow=true`：
- 复制模板脚本与 workflow 到目标仓库。
3. 运行同步脚本：
- `python scripts/sync_github_projects.py --username <username> --output <output> --limit <limit>`
- 若 `include_homepage_any_domain=true`，追加 `--include-homepage-any-domain`
- 若 `include_project_boards=true`，追加 `--include-project-boards --project-board-limit <n>`
4. 检查输出文件是否生成且 `projects` 数组非空或符合预期。
5. 若 `auto_commit=true`：
- `git add <output>`
- `git commit -m "chore: sync GitHub projects feed"`
6. 若 `auto_push=true`：
- `git push`
7. 若需要定时运行：
- 启用 `.github/workflows/sync-github-projects.yml`
- 使用 `schedule` + `workflow_dispatch` 进行自动和手动触发。

## Validation
执行后至少验证以下项目：
- `assets/github-projects.json` 可被正常解析。
- landing page `#sites` 区块能加载新项目。
- workflow 在无变更时不会产生空 commit。

## Failure Handling
- GitHub API 请求失败：
- 返回 HTTP 状态和错误摘要，不写入输出文件。
- GitHub Projects 看板缺失：
- 检查 `GITHUB_TOKEN` 是否可用于 GraphQL；若无 token，脚本会跳过看板同步。
- 输出文件为空或项目缺失：
- 检查仓库是否为 fork/private/archived，或是否缺少 Pages/homepage 配置。
- workflow 成功但页面未更新：
- 检查部署链路是否会把最新 `assets/github-projects.json` 发布到站点。

## Output Contract
每次执行应返回：
- Checked username
- Filter mode (`pages_only` / `include_homepage_any_domain`)
- Include project boards (`true` / `false`)
- Output path
- Synced project count
- Commit status (`skipped` / `success` / `failed`)
- Push status (`skipped` / `success` / `failed`)
- Next action when failed

## Example Prompts
- `/vikipedia-github-landing-sync username=ttoriaa limit=9 include_project_boards=true install_workflow=true`
- `/vikipedia-github-landing-sync username=ttoriaa include_homepage_any_domain=true include_project_boards=true auto_commit=true auto_push=true`
- `帮我给 ttoriaa/vikipedia 加一个定时同步 GitHub 项目到 landing page 的技能和 workflow。`
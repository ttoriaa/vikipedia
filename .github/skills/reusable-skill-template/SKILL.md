---
name: your-skill-name
description: "一句话说明这个 skill 的业务目标与产出。Use when you need <your trigger phrases here>."
argument-hint: "可选参数: date=YYYY-MM-DD, dry_run=true|false, deploy=true|false, dispatch_workflow=true|false"
user-invocable: true
disable-model-invocation: false
---

# Reusable Skill Template

## Purpose
一句话说明这个 skill 的业务目标与产出。

## When To Use
- 场景 1：何时触发这个 skill。
- 场景 2：什么前置工作已完成。
- 场景 3：期望得到什么结果。

## Inputs
- date (optional): YYYY-MM-DD。默认自动解析最新可用日期。
- dry_run (optional, default true): 仅本地生成与校验，不提交不发布。
- deploy (optional, default false): 是否提交并推送产物。
- dispatch_workflow (optional, default false): 是否触发 GitHub Actions workflow_dispatch。
- extra_flags (optional): 透传给脚本的附加参数。

## Prerequisites
- Python 可执行文件可用：./.venv/Scripts/python.exe
- 必要目录存在：<reports_or_input_dir>/<date>/
- 必要输入文件存在：
  - <required_file_1>
  - <required_file_2>
- 若需要 workflow_dispatch：
  - gh CLI 已安装
  - gh auth login 已完成

## Procedure
1. 解析输入参数并确定 resolved date。
2. 前置校验：目录和必要文件存在，否则终止。
3. 生成阶段（可多步）：
   - ./.venv/Scripts/python.exe ./scripts/<step1_script>.py --date <date> <extra_flags>
   - ./.venv/Scripts/python.exe ./scripts/<step2_script>.py --date <date> <extra_flags>
4. 组装或同步阶段：
   - 执行站点/报告归档复制或索引更新。
5. 校验阶段：检查关键输出文件是否全部存在。
6. 若 deploy=true：
   - 仅 add 必要文件
   - git commit -m "<type(scope): message>"
   - git push origin <branch>
7. 若 dispatch_workflow=true：
   - gh workflow run <workflow_file_or_name>
   - 若失败，保留本地产物并输出手动触发路径。

## Validation Checklist
- <output_file_1>
- <output_file_2>
- <output_file_3>
- 可选：数据完整性检查（行数 > 0，关键字段非空）

## Failure Handling
- Missing input directory:
  - 终止并提示先执行上游 pipeline。
- Missing required file:
  - 终止并提示先运行对应生成脚本。
- Build step failed:
  - 终止并返回失败脚本和错误摘要。
- Validation failed:
  - 终止并返回缺失文件清单。
- Deploy failed:
  - 返回 git 错误摘要与手动修复建议。
- Workflow dispatch failed:
  - 返回 gh 错误摘要与 GitHub UI 手动触发路径。

## Output Contract
每次执行必须返回：
- Resolved date
- Executed command list
- Validation checklist result (pass or fail)
- Deploy status (skipped or success or failed)
- Workflow dispatch status (skipped or success or failed)
- Next action when failed

## Safety Notes
- deploy=true 前必须先通过本地校验，避免发布损坏产物。
- 默认 dry_run=true，先验证再发布。
- 严格限制提交范围，只提交本次产物相关文件。
- 若仓库存在无关脏改动，不要回滚无关文件。

## Copy & Customize Steps
1. 复制目录并重命名：
   - .github/skills/reusable-skill-template -> .github/skills/<your-skill-name>
2. 替换占位符：
  - frontmatter 中的 `name`、`description`、`argument-hint`
  - <step1_script>、<required_file_1>、<output_file_1>、<workflow_file_or_name>
3. 更新 Purpose/When To Use/Failure Handling 为你的业务语义。
4. 在仓库根 README 或 .github/skills/README.md 增加入口说明。
5. 提交并推送：
   - git add .github/skills/<your-skill-name> .github/skills/README.md
   - git commit -m "feat(skill): add <your-skill-name>"
   - git push origin main

## Example Prompts
- /<your-skill-name> date=2026-06-22 dry_run=true
- /<your-skill-name> date=2026-06-22 deploy=true
- /<your-skill-name> date=2026-06-22 deploy=true dispatch_workflow=true
- 请按 <your-skill-name> 流程跑今天的数据同步并返回执行合同。

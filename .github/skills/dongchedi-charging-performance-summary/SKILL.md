---
name: dongchedi-charging-performance-summary
description: '从懂车帝参数页提取并总结汽车充电性能。Use when you need EV charging benchmark, Dongchedi batch extraction, CLTC/工信部续航, 高压快充平台, 充电时间, 充电电量 对比表。'
argument-hint: '输入一个或多个懂车帝参数页 URL，输出中英双语充电性能总结表'
user-invocable: true
disable-model-invocation: false
---

# Dongchedi Charging Performance Summary

## Purpose
产出基于懂车帝参数页的车型级充电性能总结，确保字段对齐、口径一致、缺失值透明标注，可直接用于报告、邮件或文档。

## When To Use
- 需要对多个车型做充电性能横向对比。
- 需要固定口径提取懂车帝参数页关键充电字段。
- 需要中英双语的可复用输出。

## Required Fields
每个车型必须尝试提取以下字段：
- 纯电续航里程(km)工信部
- 纯电续航里程(km)CLTC
- 高压快充平台
- 充电时间
- 充电电量

字段映射规则：
- 页面若使用 快充电量(%)，统一映射到输出列 充电电量。
- 输出列名始终保持为 充电电量，不随源页面标签变化。

## Inputs
- 一个或多个懂车帝参数页 URL（通常包含 `/auto/params-carIds-x-<id>`）。
- 可选：用户指定的目标车型名单、输出语言偏好、是否需要邮件体。

## Self-contained Quick Start
- Build summary for latest date:
	- `.\\.venv\\Scripts\\python.exe .\\.github\\skills\\dongchedi-charging-performance-summary\\scripts\\build_charging_performance_summary.py`
- Build summary for specific date:
	- `.\\.venv\\Scripts\\python.exe .\\.github\\skills\\dongchedi-charging-performance-summary\\scripts\\build_charging_performance_summary.py --date <YYYY-MM-DD>`

## Procedure
1. 收集 URL 与目标车型范围。
2. 读取页面并识别车型列（model columns）与参数行（parameter rows）。
3. 按车型逐列提取 5 个必需字段。
4. 应用字段映射：快充电量(%) -> 充电电量。
5. 校验每个字段的值数量与车型数量是否一致。
6. 对缺失、折叠、图标化或不可判读项标记为 未明确显示。
7. 生成单张 markdown 表：每行一个车型。
8. 输出中英双语结果说明与质量备注。

## Decision Points
- 若页面有结构化表格可稳定解析：优先结构化提取。
- 若结构化提取不完整：回退到页面文本检索并二次对齐车型列。
- 若字段标签变体出现：按标准字段映射归一。
- 若存在歧义或单位不清：保留原文片段并在质量备注中说明。

## Output Contract
必须输出一个 markdown 表，列顺序固定为：
- 车系ID
- 车型
- 纯电续航里程(km)工信部
- 纯电续航里程(km)CLTC
- 高压快充平台
- 充电时间
- 充电电量

并附加：
- 中英双语简短结论段。
- 质量备注：列出所有 未明确显示 项与映射假设。

## Quality Checks
完成前逐项检查：
- 车型数与每列值数一致，避免错位。
- 不臆造任何缺失值。
- 所有标签变体已归一到标准列。
- 表格字段顺序与命名完全符合 Output Contract。
- 质量备注已覆盖所有异常与假设。

## Email Delivery Rule
若用户要求邮件发送：
- 仅在存在真实邮件工具与授权时执行真实发送。
- 无法真实发送时，必须明确说明限制。
- 同时提供可直接复制的邮件主题、正文和 CSV 内容。

## Example Prompts
- /dongchedi-charging-performance-summary 对这 5 个懂车帝 URL 生成充电性能对比总结
- /dongchedi-charging-performance-summary 批量提取并输出中英双语表格，标注未明确显示字段
- /dongchedi-charging-performance-summary 生成可邮件发送版本（含主题、正文、CSV）

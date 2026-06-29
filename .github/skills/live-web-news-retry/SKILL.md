---
name: live-web-news-retry
description: "Rerun direct web news collection and regenerate HTML/Markdown/JSON output after network connectivity recovers."
argument-hint: "可选参数: date=YYYY-MM-DD, timeout=8, max_per_source=4"
user-invocable: true
disable-model-invocation: false
---

# Live Web News Retry

## Purpose
在网络恢复后，重跑网页直采新闻任务（不依赖历史 data table），并重新生成可分享的 HTML/Markdown/JSON 输出。

## When To Use
- 之前执行 `scripts/build_live_web_news_page.py` 时出现大面积 timeout。
- 你需要在网络恢复后补跑当天或指定日期的 A/B/C 新闻页面。
- 你希望拿到可直接打开的页面文件用于浏览或分享。

## Inputs
- `date` (optional): 目标日期，格式 `YYYY-MM-DD`。默认当天。
- `timeout` (optional, default `8`): 单源请求超时秒数。
- `max_per_source` (optional, default `4`): 每个源最多保留条数。

## Prerequisites
- Python 可执行文件可用：`./.venv/Scripts/python.exe`
- 脚本存在：`scripts/build_live_web_news_page.py`
- 输出目录可写：`reports/live_web_news/<date>/`

## Procedure
1. 确认网络已恢复或可访问外部 RSS/Atom 源。
2. 运行命令：
   - `./.venv/Scripts/python.exe ./scripts/build_live_web_news_page.py --timeout <timeout> --max-per-source <max_per_source>`
3. 若需要指定日期目录，可追加：
   - `--date <YYYY-MM-DD>`
4. 读取命令输出摘要（EV/Robotics/AI item 数与 failure 数）。
5. 打开并检查生成页面。

## Validation Checklist
- `reports/live_web_news/<date>/live_web_news_<date>.html`
- `reports/live_web_news/<date>/live_web_news_<date>.md`
- `reports/live_web_news/<date>/live_web_news_<date>.json`
- `item_count > 0`（至少一个板块非零）
- `failures` 显著下降（理想值为 0）

## Failure Handling
- 若仍全部 timeout：
  - 增大 `timeout`（例如 12-20）并重试。
  - 保留页面输出，用 `Source Health` 记录失败源。
- 若部分源失败：
  - 结果照常生成，标记失败源，后续可补跑。

## Output Contract
每次执行返回：
- Resolved date
- EV/Robotics/AI item counts
- failure count + failure source list
- 输出文件路径（html/md/json）

## Example Prompts
- `/live-web-news-retry`
- `/live-web-news-retry timeout=12 max_per_source=6`
- `/live-web-news-retry date=2026-06-23 timeout=15`

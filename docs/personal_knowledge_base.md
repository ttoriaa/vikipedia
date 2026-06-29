# Personal Knowledge Base for Vikipedia Agents

## Goal

Build a reusable, searchable knowledge base from four streams:

1. Conversation outcomes (decision summaries)
2. Implementation process (scripts, generated artifacts)
3. Website build process (HTML/site outputs)
4. Skill training process (SKILL definitions + execution evidence)

## Why This Works

The workspace already has stable artifacts under `reports/`, skill definitions under `.github/skills/`, and website outputs under root and `site/`. A snapshot builder can continuously turn those artifacts into one readable knowledge document.

## Script

Use:

```powershell
.\.venv\Scripts\python.exe .\scripts\build_personal_knowledge_base.py
```

Options:

```powershell
.\.venv\Scripts\python.exe .\scripts\build_personal_knowledge_base.py --date 2026-06-24 --top-skills 12 --recent-limit 15
```

## Outputs

- `reports/knowledge_base/<date>/personal_kb.md`
- `reports/knowledge_base/<date>/personal_kb.json`
- `reports/knowledge_base/latest.md`
- `reports/knowledge_base/index.html` (web view)
- `reports/knowledge_base/latest.html` (latest web snapshot)

## VS Code Tasks

Use the built-in workspace tasks:

- `Personal KB: Refresh`
- `Personal KB: Add Decision Note`

The second task prompts for structured fields and appends a decision entry.

## Daily Scheduler

Register a Windows Task Scheduler job:

```powershell
.\scripts\register_personal_kb_daily_task.ps1
```

Runner script:

```powershell
.\scripts\run_personal_kb_task_runner.ps1 -Mode run
```

This refreshes the daily snapshot and keeps `reports/knowledge_base/latest.md` up to date.

## Structured Decision Log

Decision entry script:

```powershell
.\.venv\Scripts\python.exe .\scripts\add_decision_log_entry.py --title "title" --decision "decision"
```

Outputs:

- `reports/knowledge_base/notes/YYYY-MM-DD_decisions.md`
- `reports/knowledge_base/notes/decision_log.jsonl`

Template:

- `reports/knowledge_base/templates/decision_note_template.md`

## Recommended Operating Rhythm

1. Keep existing pipelines running (Dongchedi, Daily Market News, Daily Brief).
2. After meaningful chats or implementation decisions, write short notes under `reports/knowledge_base/notes/`.
3. Rebuild this knowledge snapshot daily or after major changes.
4. Publish `latest.md` to Confluence or Feishu when needed.

## About "Thinking Process"

To keep outputs safe and practical, this knowledge base stores concise decision summaries and evidence (what was done and why), instead of hidden internal chain-of-thought.

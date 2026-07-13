---
name: bilingual-consistency-checker
description: "Validate Chinese and English field parity, glossary consistency, and section alignment for bilingual outputs. Use when you need zh-en parity checks, translation completeness, or terminology consistency before publish."
argument-hint: "optional args: input=<path>, glossary=<path>, strict=true|false, target=report|html|json"
user-invocable: true
disable-model-invocation: false
---

# Bilingual Consistency Checker

## Purpose
Ensure bilingual artifacts are complete, aligned, and terminology-consistent before publishing.

## Trigger Conditions
- A report/page includes paired Chinese and English sections.
- JSON data uses `_zh` and `_en` field conventions.
- C7 regulation or market report needs bilingual release quality gate.

## Inputs
- input (required): Markdown/HTML/JSON path to validate.
- glossary (optional): Bilingual glossary path. Default: `reports/i18n/glossary_core.json`.
- strict (optional, default true): Block on warnings when true.
- target (optional): Artifact type `report|html|json`; auto-detect if omitted.

## Output Contract
Each run must return:
- run_id
- target and scanned file count
- mismatch summary by category
- missing translation items
- terminology violations
- decision: pass | warn | block
- next_action list

## Evaluation Metrics
- translation_coverage: translated items over required items.
- key_parity_rate: `_zh`/`_en` key pair completeness.
- glossary_match_rate: terms matching approved glossary.
- section_alignment_rate: matched section headers/anchors.
- length_ratio_outlier_rate: suspiciously short/long translation ratio.
- unresolved_issue_count: final unresolved mismatch count.

## Failure Handling
- Input file missing:
  - Stop and return `ERR_INPUT_NOT_FOUND`.
- Unsupported type:
  - Stop and return `ERR_TARGET_TYPE_UNSUPPORTED`.
- Glossary missing:
  - Continue without term checks and mark warning.
- Severe parity mismatch:
  - Return `decision=block` with blocking item list.
- Non-blocking wording mismatch:
  - Return `decision=warn` with suggested replacements.

## Procedure
1. Detect artifact type and load parser.
2. Extract bilingual units (keys/sections/paragraph pairs).
3. Validate completeness and structural alignment.
4. Run glossary terminology checks.
5. Compute metrics and classify severities.
6. Emit report and machine-readable issue list.

## Minimum Runnable Example
### Glossary example (`reports/i18n/glossary_core.json`)
```json
{
  "快充": "fast charging",
  "续航": "range",
  "工信部续航": "MIIT range",
  "高压平台": "high-voltage platform"
}
```

### Input JSON example
```json
{
  "title_zh": "懂车帝每日充电简报",
  "title_en": "Dongchedi Daily Charging Brief",
  "summary_zh": "今日样本覆盖 42 款车型",
  "summary_en": "Today's sample covers 42 models"
}
```

### Run command example
```powershell
./.venv/Scripts/python.exe ./scripts/i18n/run_bilingual_check.py --input reports/dongchedi_daily/2026-07-07/report.json --glossary reports/i18n/glossary_core.json --strict true --target json
```

### Expected minimal output example
```json
{
  "run_id": "i18n-20260707-001",
  "translation_coverage": 1.0,
  "key_parity_rate": 1.0,
  "glossary_match_rate": 0.96,
  "decision": "pass"
}
```

## Safety Notes
- Never auto-translate and overwrite without explicit approval.
- Keep glossary changes version-controlled and reviewed.
- Block release if required bilingual fields are missing.

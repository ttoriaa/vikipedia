---
name: dcc-rpa-assessment
description: "Merge DCC classification and row-level processing behavior into one CSV artifact. Use when you need merged DCC RPA assessment, data dictionary plus data flow, or 字段级处理分析 CSV."
user-invocable: true
disable-model-invocation: false
---

# DCC RPA Assessment

## Purpose
Produce one merged CSV where each row remains a recognized data type, the first five columns stay aligned with the DCC dictionary contract, and appended columns capture row-level processing behavior.

## When To Use
- Start from a Confluence page, page tree, or similar feature documentation.
- You need one merged CSV that combines classification fields with collection, storage, transmission, backend usage, and gap notes.
- The output must stay row-based rather than collapsing into a prose summary.

## Inputs
- A Confluence page URL, page ID, parent page, or feature page tree.
- Optional cached page exports or reviewer-provided evidence excerpts.
- Optional DCC references used for data classification.
- Optional downstream schema requirements.

Default output schema when no downstream schema is provided:
- `data_type`
- `personal_data_class`
- `important_data_class`
- `grading_level`
- `source`
- `collection`
- `in_vehicle_storage`
- `vehicle_to_cloud_transmission`
- `backend_usage`
- `gap_notes`

## Outputs
- CSV content or a `.csv` artifact with one row per recognized data type.
- The first five columns remain exactly `data_type`, `personal_data_class`, `important_data_class`, `grading_level`, `source`.
- Missing processing evidence is kept in-row with conservative values such as `unknown` plus short `gap_notes`.

## Boundaries
- Focus on the merged row-level evidence layer that combines classification with processing behavior.
- Do not replace the CSV with a prose-only data-flow summary.
- Do not invent undocumented collection, storage, transmission, or backend usage stages.
- Do not produce final Measures Bank judgments unless explicitly requested.

## Local Deployment Notes
- This workspace currently stores the skill contract only.
- The Confluence backup page referenced additional UAT files, but they are not present in this repository.

## Sensitivity
Medium to high: may combine compliance evidence, personal-data classifications, and internal source content.

---
name: pia-measures-bank-assessment
description: "Generate the final PIA Measures Bank V4.0 assessment table in English from feature evidence. Use when you need final measures bank assessment output or merged DCC plus RPA to measures bank."
user-invocable: true
disable-model-invocation: false
---

# PIA Measures Bank Assessment

## Purpose
Act as the single workflow entry for the final PIA Measures Bank V4.0 assessment result in English.

## When To Use
- The user wants the final Measures Bank assessment table, not a generic privacy analysis.
- Inputs may include a Confluence feature page, page tree, merged DCC plus RPA CSV, or a data-usage analysis.
- The output must map evidence into the Measures Bank structure with applicability, rationale, and gaps.

## Inputs
- A Confluence parent page, single feature page, or page tree.
- An already prepared merged DCC plus RPA CSV, if available.
- A previously prepared data-usage analysis or data dictionary plus data-flow summary.
- Reference page: `https://atc.bmwgroup.net/confluence/spaces/SECMGTCN/pages/8339562510/AI+Skills+PIA+Measures+Bank+V4.0`.
- Optional local Measures Bank snapshot file.

## Outputs
- Output in pure English.
- Reproduce the final answer as a fixed-width HTML table.
- Use the Measures Bank table as the source of truth for the first four output columns.
- Keep copied bank content in a separate snapshot or data file rather than embedding the full bank directly into the skill contract.

## Boundaries
- Do not invent Measures Bank table headers or row structure if the reference page cannot be accessed.
- Do not embed the full mutable Measures Bank assessment content directly into this skill file.
- Do not invent, rewrite, translate, merge, or backfill bank values that are not present verbatim in the source table.
- Do not treat generic policy assumptions as feature evidence.

## Local Deployment Notes
- This workspace currently stores the skill contract only.
- The backup page referenced a separate snapshot artifact and UAT files, but those files are not present in this repository.

## Sensitivity
Medium to high: may combine compliance evidence, personal-data classifications, and internal source content.

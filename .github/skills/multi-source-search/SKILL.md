---
name: multi-source-search
description: "Route and combine searches across Confluence, GitHub, and Jira for one integrated answer. Use when you need federated evidence, cross-system lookup, or 多源检索."
user-invocable: true
disable-model-invocation: false
---

# Multi-Source Search

## Purpose
Route and combine searches across Confluence, GitHub, and Jira for one integrated answer.

## When To Use
- A request requires combined evidence from at least two systems.
- You need unified synthesis with source-attributed findings.
- A single-system skill would be insufficient.

## Inputs
- User question requiring cross-system evidence.
- Preferred source priority or time window.
- Optional output format for comparison or synthesis.

## Outputs
- Source-grouped findings with attribution.
- Cross-source consistency and conflict notes.
- Consolidated conclusion plus open questions.

## Boundaries
- Use when at least two systems are required.
- If one system is sufficient, route to the dedicated skill instead.
- Keep source attribution explicit.

## Local Deployment Notes
- The Confluence backup referenced only the skill contract and UAT metadata.
- This repository now contains the local skill contract so Copilot can route the workflow.

## Sensitivity
Medium to high: may combine compliance evidence, personal-data classifications, and internal source content.

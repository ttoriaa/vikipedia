---
name: github-search
description: "Find relevant source artifacts from GitHub for technical or compliance context. Use when you need GitHub search, repository evidence retrieval, or issue and code lookup."
user-invocable: true
disable-model-invocation: false
---

# GitHub Search

## Purpose
Find relevant source artifacts from GitHub for technical or compliance context.

## When To Use
- You need repository, code, issue, or PR evidence.
- The task is read-only and evidence-focused.
- The result should support technical or compliance analysis.

## Inputs
- Repository or organization scope.
- Search terms, issue IDs, file paths, or technical questions.
- Optional time window or source-priority hints.

## Outputs
- Relevant GitHub artifacts with short relevance notes.
- Evidence snippets or references grouped by source type.
- Any access limitations encountered.

## Boundaries
- Read-focused operation only.
- Prefer precise repository-scoped retrieval when possible.
- Do not turn search-only workflows into write operations.

## Local Deployment Notes
- The backup page described this as a reusable skill contract only.
- Any helper automation referenced outside this repository will need to be added separately.

## Sensitivity
Medium: read-only searches can expose internal page, issue, repository, and code details.

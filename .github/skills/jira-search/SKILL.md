---
name: jira-search
description: "Retrieve Jira planning and execution evidence relevant to the request. Use when you need Jira search, issue retrieval, or planning evidence lookup."
user-invocable: true
disable-model-invocation: false
---

# Jira Search

## Purpose
Retrieve Jira planning and execution evidence relevant to the request.

## When To Use
- You need issue, planning, status, or execution evidence from Jira.
- The workflow is read-only.
- The result should support a compliance or technical answer.

## Inputs
- Project, issue key, search terms, or Jira query scope.
- Optional status, assignee, or time filters.
- Optional extraction focus such as ownership, timing, or decision evidence.

## Outputs
- Relevant Jira artifacts with short relevance notes.
- Evidence snippets or structured findings.
- Any access limitations encountered.

## Boundaries
- Read-focused operation only.
- Keep retrieval scoped to the question being answered.
- For modifications, hand off to `jira-update`.

## Local Deployment Notes
- This local deployment provides the skill routing contract.
- Helper assets referenced in the Confluence backup are not present in this repository.

## Sensitivity
Medium: read-only searches can expose internal page, issue, repository, and code details.

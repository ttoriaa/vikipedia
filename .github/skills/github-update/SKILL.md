---
name: github-update
description: "Prepare and coordinate GitHub-side updates with clear, auditable intent. Use when you need GitHub update planning, repository changes, or traceable write operations."
user-invocable: true
disable-model-invocation: false
---

# GitHub Update

## Purpose
Prepare and coordinate GitHub-side updates with clear, auditable intent.

## When To Use
- You need to modify GitHub-hosted artifacts such as repository content, issues, or workflow-facing resources.
- The change should remain scoped and auditable.
- A proposal-first workflow is preferred before execution.

## Inputs
- Target repository or artifact.
- Intended change scope and payload.
- Optional execution constraints or approval requirements.

## Outputs
- Change plan or executed update summary.
- Traceable intent mapping.
- Failure details when access or target validation fails.

## Boundaries
- Prefer proposal-first behavior unless the user explicitly asks for execution.
- Keep write scope narrow and auditable.
- Require explicit confirmation for material write operations.

## Local Deployment Notes
- This repository now contains the local skill contract.
- Helper scripts or external automation referenced in the Confluence backup are not present here.

## Sensitivity
High: can modify external systems and requires explicit execution confirmation plus scoped credentials.

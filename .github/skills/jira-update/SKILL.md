---
name: jira-update
description: "Perform structured Jira updates with explicit intent and traceability. Use when you need Jira write operations, issue updates, or controlled ticket changes."
argument-hint: "可选参数: issue=<KEY>, intent=<goal>, summary=<text>, description=<text>, description_file=<path>, comment=<text>, comment_file=<path>, labels_add=a b, labels_set=a b, apply=true|false"
user-invocable: true
disable-model-invocation: false
---

# Jira Update

## Purpose
Perform structured Jira updates with explicit intent and traceability.

## When To Use
- You need to modify issues, comments, fields, or other Jira records.
- The update should stay explicit, scoped, and reviewable.
- The task is a write operation rather than read-only retrieval.

## Inputs
- Target issue or Jira object.
- Intended change content and scope.
- Optional field-specific updates or comment content.

## Outputs
- Change plan or executed update summary.
- Before and after intent mapping.
- Failure details when validation or access fails.

## Boundaries
- Confirm target and change intent before execution.
- Prefer proposal-first behavior unless the user explicitly asks for immediate update.
- Keep write scope narrow and traceable.

## Local Deployment Notes
- This local deployment provides the skill contract only.
- Helper assets referenced by the Confluence backup are not present in this repository.

## Sensitivity
High: can modify external systems and requires explicit execution confirmation plus scoped credentials.

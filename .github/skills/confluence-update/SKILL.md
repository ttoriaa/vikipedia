---
name: confluence-update
description: "Perform controlled Confluence updates for CC and ATC via PAT-backed local scripts. Use when you need page update, labels, comments, or structured Confluence corrections with traceable intent."
argument-hint: "可选参数: instance=atc|cc, page_ref=<id-or-url>, title=<new-title>, body_file=<path>, body_text=<text>, append_file=<path>, append_text=<text>, replace_old=<text>, replace_new=<text>, apply=true|false"
user-invocable: true
disable-model-invocation: false
---

# Confluence Update

## Purpose
Perform controlled updates for both CC and ATC through local skill scripts and PAT authentication.

## When To Use
- You need to create or update page content, labels, comments, or structured corrections.
- The requested change should stay traceable and scoped.
- The task is intended to modify Confluence rather than only read it.

## Inputs
- Target page identifier such as URL or page ID.
- Intended change content and scope.
- Optional metadata changes such as labels or comments.

## Outputs
- Change plan or executed update summary.
- Before and after intent mapping.
- Failure details when access or page validation fails.

## Boundaries
- Confirm target and change intent before execution.
- Prefer proposal-first behavior unless the user explicitly asks for immediate update.
- For CC and ATC updates, prefer a workspace-local update script and PAT-backed API access.
- If the matching PAT or base URL is missing, report the direct-access configuration gap explicitly.

## Setup And Dependencies
- `ATC_CONFLUENCE_BASE_URL`
- `ATC_CONFLUENCE_TOKEN`
- `CC_CONFLUENCE_BASE_URL`
- `CC_CONFLUENCE_TOKEN`

## Local Deployment Notes
- The backup page referenced helper scripts and UAT files, but those files are not present in this repository.
- This local deployment provides the routing contract only.

## Sensitivity
High: can modify external systems and requires explicit execution confirmation plus scoped credentials.

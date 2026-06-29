---
name: confluence-bulk-page-ops
description: "Perform controlled batch operations on a root Confluence page and all descendants. Use when you need subtree batch update, bulk label changes, body replace, or page-tree bulk operations."
user-invocable: true
disable-model-invocation: false
---

# Confluence Bulk Page Ops

## Purpose
Perform controlled batch operations on a root Confluence page and all descendant pages using PAT-backed local scripts.

## When To Use
- You need bulk read or export, label append, body replace, or restriction-template updates.
- The target scope is one root page plus descendants.
- The workflow should default to dry-run first.

## Inputs
- Target instance and root page identifier.
- Operation type such as `read`, `labels`, `body-replace`, or `restrictions-template`.
- Scope controls including root inclusion, page limit, and optional depth.
- Explicit execute confirmation when leaving dry-run mode.

## Outputs
- Scope summary including instance, root page, and total pages in scope.
- Dry-run action plan or executed result summary.
- Per-page success and failure details.

## Boundaries
- Dry-run first by default.
- Keep the operation scoped to one root page and descendants.
- Require explicit confirmation for write operations.
- Report partial failures clearly instead of silently skipping them.

## Setup And Dependencies
- PAT-backed local scripts for CC or ATC Confluence access.

## Local Deployment Notes
- The Confluence backup referenced additional helper assets that are not present in this repository.
- This local deployment provides the reusable skill contract.

## Sensitivity
High: can modify external systems and requires explicit execution confirmation plus scoped credentials.

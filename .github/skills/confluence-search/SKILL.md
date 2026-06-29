---
name: confluence-search
description: "Search and retrieve Confluence content for both CC and ATC via PAT-backed local scripts. Use when you need CC Confluence search, ATC Confluence search, CQL query, or page-tree retrieval."
argument-hint: "可选参数: instance=atc|cc, mode=keyword|cql|page|page-tree, query=<text>, cql=<query>, page_ref=<id-or-url>, space_key=<SPACE>, ancestor=<id-or-url>, limit=10, max_depth=1, include_body=true|false"
user-invocable: true
disable-model-invocation: false
---

# Confluence Search

## Purpose
Search and retrieve Confluence content for both CC and ATC via PAT-backed local-script retrieval.

## When To Use
- You need page discovery, hierarchy lookup, keyword search, CQL retrieval, or evidence extraction.
- The target can be CC or ATC Confluence.
- The task is read-only.

## Inputs
- Search target: URL, space key, page ID, keywords, or CQL query.
- Retrieval depth: single page, subtree, or scoped space search.
- Optional extraction focus such as data fields, controls, ownership, or dates.

## Outputs
- Relevant pages with short relevance notes.
- Key evidence snippets mapped to source locations.
- Any access or filter limitations encountered.

## Boundaries
- Read-focused operation only.
- For page edits, hand off to `confluence-update`.
- Do not rely on workspace MCP APIs as the primary implementation path.
- Keep the direct PAT-backed local-script path for both CC and ATC.

## Setup And Dependencies
- `ATC_CONFLUENCE_BASE_URL`
- `ATC_CONFLUENCE_TOKEN`
- `CC_CONFLUENCE_BASE_URL`
- `CC_CONFLUENCE_TOKEN`

## Local Deployment Notes
- The backup page referenced helper scripts and UAT files, but those files are not present in this repository.
- This local deployment provides the skill contract so Copilot can route the request.

## Sensitivity
Medium: read-only searches can expose internal page, issue, repository, and code details.

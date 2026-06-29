# Feishu Writing Format Spec

This specification standardizes how research content is written into Feishu docs.

## 1. Heading Hierarchy

- Use exactly one H1 for the document title.
- Use H2 for top-level sections.
- Use H3 only for subsection detail under each H2.
- Do not skip heading levels (for example, H2 directly to H4).

Recommended section structure:

1. H1: Report Title
2. H2: Executive Summary
3. H2: Scope and Method
4. H2: Key Findings
5. H2: Structured Comparison
6. H2: Risks and Open Questions
7. H2: Next Actions
8. H2: Sources

## 2. Content Blocks

- Executive Summary: 3 to 5 bullets, each one sentence.
- Scope and Method: objective, search window, source types, filtering criteria.
- Key Findings: grouped by category, each group has conclusion plus evidence.
- Risks and Open Questions: list unknowns, conflicts, and validation needs.
- Next Actions: owner, due date, and expected output when available.

## 3. Table Field Standard

Use this schema for evidence comparison tables.

| Field | Required | Rule |
| --- | --- | --- |
| ID | Yes | Sequential label, for example `R1`, `R2` |
| Category | Yes | One normalized topic category |
| Claim | Yes | Atomic statement, no mixed claims |
| Evidence Summary | Yes | 1 to 2 short sentences |
| Source Title | Yes | Original page title |
| Source URL | Yes | Full URL |
| Source Date | No | Use `YYYY-MM-DD` when available |
| Confidence | Yes | One of `High`, `Medium`, `Low` |
| Notes | No | Ambiguities, caveats, follow-up |

## 4. Citation Standard

- Use inline citation tags in this format: `[S1]`, `[S2]`, `[S3]`.
- Every factual claim in summary sections should map to at least one source tag.
- In the Sources section, keep source IDs stable and unique.

Source list format:

| Source ID | Title | URL | Accessed Date |
| --- | --- | --- | --- |
| S1 | Example Source | https://example.com | 2026-05-26 |

## 5. Language and Style

- Default language: Chinese.
- Keep sentences concise and decision-oriented.
- Prefer bullets and tables over long narrative paragraphs.
- Clearly mark uncertain statements using `Pending Validation`.

## 6. Write Modes

- Default mode: append-only.
- Replacement mode is allowed only when explicit target sections are provided.
- When appending, add a timestamped H2 section title, for example `Update 2026-05-26`.

## 7. Pre-Publish Checklist

- Heading structure follows Section 1.
- All required table fields are present.
- All key claims contain source tags.
- Sources section has valid URLs.
- Conflicts and unknowns are explicitly listed.
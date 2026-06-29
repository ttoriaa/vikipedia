---
name: html-slide-deck-generator
description: "Generate standalone HTML slide decks from PPT-style context with editable theme tokens and scaffold/final output modes. Use when you need ppt-style html deck generation, editable html presentation scaffold, or fast wording/design iteration."
argument-hint: "Optional parameters: source_ppt=<path>, content_input=<path>, output_mode=final-deck|scaffold, output_dir=<path>, deck_title=<text>, language=zh|en|bilingual"
user-invocable: true
disable-model-invocation: false
---

# HTML Slide Deck Generator

## Purpose
Generate a standalone HTML slide deck from a PowerPoint-style context while preserving the source visual direction and keeping an editable structure for wording and design iteration.

## When To Use
- You need an HTML presentation that keeps the style intent of an existing PPT template.
- You want quick post-generation edits to slide text, layout rhythm, and visual tokens.
- You need a reusable scaffold for repeated deck generation workflows.

## Inputs
- source_ppt (optional): Source PowerPoint file used as style reference.
- content_input: Structured slide content in JSON or markdown-like outline.
- output_mode (optional, default scaffold): `final-deck` or `scaffold`.
- output_dir (optional): Output directory for generated artifacts.
- deck_title (optional): Title for generated HTML deck.
- language (optional): `zh`, `en`, or `bilingual`.

## Workflow
1. Parse or infer theme tokens from source PPT style reference.
2. Normalize input content into slide sections and presentation blocks.
3. Render standalone HTML deck with embedded CSS variables.
4. Emit optional scaffold assets for iterative edits.
5. Validate generated deck structure and token completeness.

## Output
- Standalone HTML slide deck with local-only assets.
- Theme snapshot JSON for reusable style tokens.
- Editable scaffold deck for follow-up text/design changes.

## Commands
- Extract style snapshot:
  - `./.venv/Scripts/python.exe ./.github/skills/html-slide-deck-generator/scripts/extract_ppt_theme.py --source-ppt <path> --output ./.github/skills/html-slide-deck-generator/fixtures/theme_snapshot.json`
- Render HTML deck:
  - `./.venv/Scripts/python.exe ./.github/skills/html-slide-deck-generator/scripts/render_html_slide_deck.py --content <path> --theme ./.github/skills/html-slide-deck-generator/fixtures/theme_snapshot.json --output <output_html>`
- Validate fixture/deck:
  - `./.venv/Scripts/python.exe ./.github/skills/html-slide-deck-generator/scripts/validate_fixture.py --fixture ./.github/skills/html-slide-deck-generator/fixtures/sample_deck.json`

## Boundaries
- Do not treat the source PPT as runtime content input; it is only a design baseline.
- Do not claim pixel-perfect conversion of every animation/master variant.
- Do not fetch remote assets during rendering.
- Keep output fully editable instead of hard-coding non-semantic absolute positioning.

## Safety Notes
Medium: review source material before sharing outside intended audience.
- Publish environment variable names only, never secret values.
- Do not commit generated caches, bytecode files, or private enterprise source data.

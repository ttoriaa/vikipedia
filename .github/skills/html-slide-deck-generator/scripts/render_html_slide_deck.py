import argparse
import json
from pathlib import Path


def render_html(content: dict, theme: dict, title: str) -> str:
    slides = content.get("slides", [])
    colors = theme.get("colors", {})
    typography = theme.get("typography", {})
    spacing = theme.get("spacing", {})

    css_vars = f"""
    :root {{
      --bg: {colors.get('bg', '#f7f3ea')};
      --surface: {colors.get('surface', '#fffdf7')};
      --text: {colors.get('text', '#1f1f1f')};
      --muted: {colors.get('muted', '#5b5b5b')};
      --accent: {colors.get('accent', '#0e6d53')};
      --accent-2: {colors.get('accent_2', '#d97a28')};
      --title-font: {typography.get('title', "'Georgia', serif")};
      --body-font: {typography.get('body', "'Noto Serif SC', serif")};
      --slide-padding: {spacing.get('slide_padding', '42px')};
      --block-gap: {spacing.get('block_gap', '16px')};
    }}
    """

    slide_html = []
    for idx, s in enumerate(slides, start=1):
        bullets = "".join(f"<li>{b}</li>" for b in s.get("bullets", []))
        slide_html.append(
            f"""
            <section class=\"slide\">
              <div class=\"badge\">Slide {idx}</div>
              <h2>{s.get('title', '')}</h2>
              <p class=\"lead\">{s.get('lead', '')}</p>
              <ul>{bullets}</ul>
            </section>
            """
        )

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
  <style>
    {css_vars}
    body {{ margin: 0; background: linear-gradient(180deg, var(--bg), #efe8d8); color: var(--text); font-family: var(--body-font); }}
    .deck {{ max-width: 1100px; margin: 0 auto; padding: 30px; display: grid; gap: 24px; }}
    .hero {{ background: var(--surface); border: 1px solid #ddd2bc; border-radius: 16px; padding: var(--slide-padding); }}
    h1, h2 {{ font-family: var(--title-font); margin: 0 0 10px; }}
    .slide {{ background: var(--surface); border: 1px solid #ddd2bc; border-radius: 16px; padding: var(--slide-padding); }}
    .lead {{ color: var(--muted); margin: 0 0 var(--block-gap); }}
    .badge {{ display: inline-block; font-size: 12px; letter-spacing: .08em; text-transform: uppercase; background: var(--accent); color: #fff; padding: 4px 8px; border-radius: 999px; margin-bottom: 10px; }}
    li {{ margin-bottom: 8px; }}
    @media (max-width: 800px) {{ .deck {{ padding: 14px; }} .hero, .slide {{ padding: 24px; }} }}
  </style>
</head>
<body>
  <main class=\"deck\">
    <section class=\"hero\">
      <h1>{title}</h1>
      <p class=\"lead\">Generated HTML slide deck scaffold. Edit content blocks and CSS tokens as needed.</p>
    </section>
    {''.join(slide_html)}
  </main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render standalone HTML slide deck from content + theme tokens.")
    parser.add_argument("--content", required=True, help="JSON content file path.")
    parser.add_argument("--theme", required=True, help="Theme snapshot JSON path.")
    parser.add_argument("--output", required=True, help="Output HTML path.")
    parser.add_argument("--title", default="HTML Slide Deck", help="Deck title.")
    args = parser.parse_args()

    content = json.loads(Path(args.content).read_text(encoding="utf-8"))
    theme = json.loads(Path(args.theme).read_text(encoding="utf-8"))
    html = render_html(content, theme, args.title)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Deck rendered: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

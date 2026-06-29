import argparse
import json
from pathlib import Path


def build_default_theme(source_ppt: str) -> dict:
    # Keep theme lightweight and editable; this is a baseline token snapshot.
    return {
        "source_ppt": source_ppt,
        "colors": {
            "bg": "#f7f3ea",
            "surface": "#fffdf7",
            "text": "#1f1f1f",
            "muted": "#5b5b5b",
            "accent": "#0e6d53",
            "accent_2": "#d97a28"
        },
        "typography": {
            "title": "'Georgia', 'Times New Roman', serif",
            "body": "'Noto Serif SC', 'PingFang SC', serif"
        },
        "spacing": {
            "slide_padding": "42px",
            "block_gap": "16px"
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract or initialize PPT theme tokens for HTML deck rendering.")
    parser.add_argument("--source-ppt", required=True, help="Path to source PPT used as visual reference.")
    parser.add_argument("--output", required=True, help="Output JSON path for theme snapshot.")
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    theme = build_default_theme(args.source_ppt)
    out_path.write_text(json.dumps(theme, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Theme snapshot written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate HTML slide deck fixture schema.")
    parser.add_argument("--fixture", required=True, help="Fixture JSON path.")
    args = parser.parse_args()

    path = Path(args.fixture)
    data = json.loads(path.read_text(encoding="utf-8"))

    slides = data.get("slides")
    if not isinstance(slides, list) or len(slides) < 3:
        raise SystemExit("Fixture must include at least 3 slides.")

    for i, slide in enumerate(slides, start=1):
        if not slide.get("title"):
            raise SystemExit(f"Slide {i} missing title.")
        if "bullets" in slide and not isinstance(slide["bullets"], list):
            raise SystemExit(f"Slide {i} bullets must be a list.")

    print(f"Fixture valid: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

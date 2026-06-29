from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


def _resolve_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "reports").exists() and (parent / "dongchedi_price_map.csv").exists():
            return parent
    return current.parents[1]


ROOT = _resolve_root()
REPORT_ROOT = ROOT / "reports" / "dongchedi_daily"
load_dotenv(ROOT / ".env")


def _config() -> tuple[str, str, str, int]:
    base_url = os.getenv("FEISHU_BASE_URL", "https://open.feishu.cn").strip().rstrip("/")
    app_id = os.getenv("FEISHU_APP_ID", "").strip()
    app_secret = os.getenv("FEISHU_APP_SECRET", "").strip()
    timeout_raw = os.getenv("FEISHU_TIMEOUT_SECONDS", "30").strip()

    if not app_id or not app_secret:
        raise RuntimeError("Missing Feishu credentials. Set FEISHU_APP_ID and FEISHU_APP_SECRET in .env")

    try:
        timeout_seconds = int(timeout_raw)
    except Exception:
        timeout_seconds = 30

    return base_url, app_id, app_secret, max(5, min(timeout_seconds, 120))


def _tenant_access_token() -> str:
    base_url, app_id, app_secret, timeout_seconds = _config()
    response = requests.post(
        f"{base_url}/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=timeout_seconds,
    )

    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Feishu auth HTTP error {response.status_code}: {detail}")

    payload = response.json()
    code = int(payload.get("code", -1))
    if code != 0:
        raise RuntimeError(f"Feishu auth API error {code}: {payload.get('msg', '')}")

    token = str(payload.get("tenant_access_token", "")).strip()
    if not token:
        raise RuntimeError("Feishu auth succeeded but no tenant_access_token was returned.")
    return token


def _request(method: str, path: str, *, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
    base_url, _, _, timeout_seconds = _config()
    token = _tenant_access_token()
    response = requests.request(
        method=method,
        url=f"{base_url}{path}",
        json=json_body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        timeout=timeout_seconds,
    )

    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Feishu API HTTP error {response.status_code}: {detail}")

    payload = response.json()
    code = int(payload.get("code", -1))
    if code != 0:
        raise RuntimeError(f"Feishu API error {code}: {payload.get('msg', '')}")
    return payload


def _latest_report_dir() -> Path:
    if not REPORT_ROOT.exists():
        raise FileNotFoundError(f"Report root not found: {REPORT_ROOT}")
    dates = [p for p in REPORT_ROOT.iterdir() if p.is_dir() and p.name[:4].isdigit()]
    if not dates:
        raise FileNotFoundError("No report date folders found under reports/dongchedi_daily")
    return sorted(dates)[-1]


def _report_dir(report_date: str) -> Path:
    return REPORT_ROOT / report_date


def _load_text_preview(report_dir: Path) -> str:
    summary_path = report_dir / "summary.md"
    perf_path = report_dir / "charging_performance_summary.md"
    filtered_csv = report_dir / "filtered.csv"

    lines: list[str] = [f"Update {report_dir.name}", "Dongchedi Charging Daily Pipeline"]

    if summary_path.exists():
        for line in summary_path.read_text(encoding="utf-8").splitlines()[:40]:
            line = line.strip()
            if line:
                lines.append(line)
    if perf_path.exists():
        lines.append("Charging Performance Summary")
        for line in perf_path.read_text(encoding="utf-8").splitlines()[:24]:
            line = line.strip()
            if line:
                lines.append(line)
    if filtered_csv.exists():
        lines.append(f"Artifact: {filtered_csv.relative_to(ROOT)}")

    cleaned: list[str] = []
    for line in lines:
        compact = " ".join(line.split())
        if compact:
            cleaned.append(compact[:500])
    return "\n".join(cleaned[:100])


def _build_children(text: str) -> list[dict[str, Any]]:
    children: list[dict[str, Any]] = []
    for raw_line in [line.strip() for line in text.splitlines() if line.strip()]:
        children.append(
            {
                "block_type": 2,
                "paragraph": {
                    "elements": [
                        {
                            "text_run": {"content": raw_line},
                        }
                    ]
                },
            }
        )
    return children


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append Dongchedi daily artifacts into a Feishu doc.")
    parser.add_argument("--date", default="", help="Target report date in YYYY-MM-DD. Defaults to latest report dir.")
    parser.add_argument("--document-id", default=os.getenv("FEISHU_DEFAULT_DOC_TOKEN", "").strip(), help="Feishu doc token.")
    parser.add_argument("--parent-block-id", default=os.getenv("FEISHU_DEFAULT_PARENT_BLOCK_ID", "").strip(), help="Optional Feishu parent block id; defaults to doc root.")
    parser.add_argument("--dry-run", action="store_true", help="Preview payload without calling Feishu API.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_dir = _report_dir(args.date) if args.date else _latest_report_dir()
    if not report_dir.exists():
        raise FileNotFoundError(f"Report directory not found: {report_dir}")

    document_id = args.document_id.strip()
    if not document_id:
        raise RuntimeError("Missing Feishu document id. Pass --document-id or set FEISHU_DEFAULT_DOC_TOKEN in .env")
    parent_block_id = args.parent_block_id.strip() or document_id

    text = _load_text_preview(report_dir)
    children = _build_children(text)
    if not children:
        raise RuntimeError(f"No publishable content found in {report_dir}")

    if args.dry_run:
        print(json.dumps({
            "status": "dry_run",
            "report_dir": str(report_dir),
            "document_id": document_id,
            "parent_block_id": parent_block_id,
            "blocks": len(children),
            "preview": text[:1200],
        }, ensure_ascii=False, indent=2))
        return 0

    payload = _request(
        "POST",
        f"/open-apis/docx/v1/documents/{document_id}/blocks/{parent_block_id}/children",
        json_body={"children": children},
    )
    data = payload.get("data", {}) if isinstance(payload.get("data", {}), dict) else {}
    children_data = data.get("children", []) if isinstance(data.get("children", []), list) else []
    print(json.dumps({
        "status": "ok",
        "report_dir": str(report_dir),
        "document_id": document_id,
        "parent_block_id": parent_block_id,
        "appended_blocks": len(children_data) if children_data else len(children),
        "preview": text[:400],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

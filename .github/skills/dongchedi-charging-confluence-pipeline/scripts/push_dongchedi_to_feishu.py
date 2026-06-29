from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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


def _paragraph_block(text: str) -> dict[str, Any]:
    return {
        "block_type": 2,
        "text": {
            "elements": [
                {
                    "text_run": {"content": text},
                }
            ],
            "style": {"align": 1},
        },
    }


def _heading_block(text: str, level: int = 1) -> dict[str, Any]:
    prefix = "#" * max(1, min(level, 3))
    return _paragraph_block(f"{prefix} {text}")


def _is_md_table_row(line: str) -> bool:
    return line.startswith("|") and line.endswith("|") and line.count("|") >= 2


def _split_md_table_row(line: str) -> list[str]:
    cols = [c.strip() for c in line.strip("|").split("|")]
    return cols


def _is_md_table_separator(line: str) -> bool:
    cols = _split_md_table_row(line)
    if not cols:
        return False
    for c in cols:
        token = c.replace(" ", "")
        if not token:
            return False
        if set(token) - {"-", ":"}:
            return False
    return True


def _is_numeric_like(value: str) -> bool:
    v = value.strip().replace(",", "")
    if not v:
        return False
    return bool(re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:%)?", v))


def _pick_key_columns(rows: list[list[str]], max_cols: int = 5) -> list[int]:
    if not rows:
        return []
    header = rows[0]
    width = len(header)
    if width <= max_cols:
        return list(range(width))

    keywords = [
        "品牌", "车型", "车系", "快充", "续航", "电池", "平台", "price", "range", "charge", "battery",
    ]

    picked: list[int] = []
    for i, name in enumerate(header):
        name_l = name.lower()
        if any(k in name_l for k in keywords):
            picked.append(i)
    if 0 not in picked:
        picked.insert(0, 0)

    unique: list[int] = []
    for i in picked:
        if i not in unique:
            unique.append(i)

    if len(unique) < max_cols:
        for i in range(width):
            if i not in unique:
                unique.append(i)
            if len(unique) >= max_cols:
                break

    return sorted(unique[:max_cols])


def _render_table_rows(rows: list[list[str]], title: str | None = None) -> list[str]:
    if not rows or not rows[0]:
        return []

    keep = _pick_key_columns(rows)
    pruned = [[r[i] if i < len(r) else "" for i in keep] for r in rows]

    width = max(len(r) for r in pruned)
    normalized = [r + [""] * (width - len(r)) for r in pruned]
    col_widths = [max(len(r[i]) for r in normalized) for i in range(width)]

    numeric_cols: list[bool] = []
    for i in range(width):
        vals = [r[i] for r in normalized[1:] if r[i].strip()]
        if not vals:
            numeric_cols.append(False)
            continue
        numeric_cols.append(sum(1 for v in vals if _is_numeric_like(v)) >= max(1, int(len(vals) * 0.6)))

    def fmt(row: list[str]) -> str:
        padded: list[str] = []
        for i in range(width):
            cell = row[i]
            if numeric_cols[i] and row is not normalized[0]:
                padded.append(cell.rjust(col_widths[i]))
            else:
                padded.append(cell.ljust(col_widths[i]))
        return "| " + " | ".join(padded) + " |"

    lines: list[str] = []
    if title:
        lines.append(f"### {title}")
    lines.append(fmt(normalized[0]))
    sep = "| " + " | ".join("-" * w for w in col_widths) + " |"
    lines.append(sep)
    for row in normalized[1:]:
        lines.append(fmt(row))
    lines.append("")
    return lines


def _build_children(text: str, *, report_date: str) -> list[dict[str, Any]]:
    children: list[dict[str, Any]] = []
    children.append(_heading_block(f"Dongchedi Charging Daily {report_date}", level=1))

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    i = 0
    while i < len(lines):
        raw_line = lines[i]
        normalized = " ".join(raw_line.split())
        if _is_md_table_row(normalized):
            prev = lines[i - 1] if i > 0 else ""
            table_title = ""
            if prev.startswith("## "):
                table_title = prev[3:].strip()
            elif prev.startswith("### "):
                table_title = prev[4:].strip()
            elif prev and not prev.startswith("|") and not prev.startswith("-"):
                table_title = prev[:80]

            table_rows: list[list[str]] = []
            while i < len(lines) and _is_md_table_row(lines[i]):
                candidate = " ".join(lines[i].split())
                if _is_md_table_separator(candidate):
                    i += 1
                    continue
                table_rows.append(_split_md_table_row(candidate))
                i += 1

            rendered = _render_table_rows(table_rows, title=table_title or None)
            if rendered:
                for row_line in rendered:
                    children.append(_paragraph_block(row_line))
            continue

        if normalized.startswith("# "):
            children.append(_heading_block(normalized[2:].strip(), level=1))
        elif normalized.startswith("## "):
            children.append(_heading_block(normalized[3:].strip(), level=2))
        elif normalized.startswith("### "):
            children.append(_heading_block(normalized[4:].strip(), level=3))
        else:
            children.append(_paragraph_block(normalized))
        i += 1

    children.append(_paragraph_block(f"Generated from report: reports/dongchedi_daily/{report_date}"))
    return children


def _extract_doc_token(document_id_or_url: str) -> str:
    raw = (document_id_or_url or "").strip()
    if not raw:
        return ""

    # Token form already provided.
    if "/" not in raw and raw.startswith(("doc", "wiki", "dox")):
        return raw

    try:
        parsed = urlparse(raw)
    except Exception:
        parsed = None

    if parsed and parsed.path:
        path = parsed.path.rstrip("/")
        # Typical Feishu wiki/docx URL forms:
        # https://{tenant}.feishu.cn/wiki/{token}
        # https://{tenant}.feishu.cn/docx/{token}
        m = re.search(r"/(?:wiki|docx)/([A-Za-z0-9_-]+)$", path)
        if m:
            return m.group(1)

    # Best-effort fallback for raw strings containing a terminal token-like segment.
    m = re.search(r"([A-Za-z0-9_-]{10,})$", raw)
    return m.group(1) if m else raw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append Dongchedi daily artifacts into a Feishu doc.")
    parser.add_argument("--date", default="", help="Target report date in YYYY-MM-DD. Defaults to latest report dir.")
    parser.add_argument("--document-id", default=os.getenv("FEISHU_DEFAULT_DOC_TOKEN", "").strip(), help="Feishu doc token or full Feishu document URL.")
    parser.add_argument("--parent-block-id", default=os.getenv("FEISHU_DEFAULT_PARENT_BLOCK_ID", "").strip(), help="Optional Feishu parent block id; defaults to doc root.")
    parser.add_argument("--dry-run", action="store_true", help="Preview payload without calling Feishu API.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_dir = _report_dir(args.date) if args.date else _latest_report_dir()
    if not report_dir.exists():
        raise FileNotFoundError(f"Report directory not found: {report_dir}")

    document_id = _extract_doc_token(args.document_id)
    if not document_id:
        raise RuntimeError("Missing Feishu document id. Pass --document-id or set FEISHU_DEFAULT_DOC_TOKEN in .env")
    parent_block_id = args.parent_block_id.strip() or document_id

    text = _load_text_preview(report_dir)
    children = _build_children(text, report_date=report_dir.name)
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

    appended_total = 0
    # Feishu docx API allows at most 50 child blocks per request.
    for i in range(0, len(children), 50):
        chunk = children[i:i + 50]
        payload = _request(
            "POST",
            f"/open-apis/docx/v1/documents/{document_id}/blocks/{parent_block_id}/children",
            json_body={"children": chunk},
        )
        data = payload.get("data", {}) if isinstance(payload.get("data", {}), dict) else {}
        children_data = data.get("children", []) if isinstance(data.get("children", []), list) else []
        appended_total += len(children_data) if children_data else len(chunk)
    print(json.dumps({
        "status": "ok",
        "report_dir": str(report_dir),
        "document_id": document_id,
        "parent_block_id": parent_block_id,
        "appended_blocks": appended_total,
        "preview": text[:400],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

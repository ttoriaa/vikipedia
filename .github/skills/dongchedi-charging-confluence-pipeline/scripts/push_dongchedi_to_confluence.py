from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from typing import Any

import requests

def _resolve_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "reports").exists() and (parent / "dongchedi_price_map.csv").exists():
            return parent
    return p.parents[1]


ROOT = _resolve_root()
ENV_PATH = ROOT / ".env"
REPORT_DIR = ROOT / "reports" / "dongchedi_daily"


def load_env() -> dict[str, str]:
    data: dict[str, str] = {}
    for line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip().lstrip("\ufeff")] = value.strip()
    return data


def request(base_url: str, method: str, path: str, email: str, token: str, *, params: dict[str, Any] | None = None, json_body: dict[str, Any] | None = None, auth_mode: str = "auto") -> requests.Response:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    url = base_url.rstrip("/") + path
    if auth_mode == "basic":
        return requests.request(method, url, params=params, json=json_body, headers=headers, auth=(email, token), timeout=30)
    if auth_mode == "bearer":
        headers = dict(headers)
        headers["Authorization"] = f"Bearer {token}"
        return requests.request(method, url, params=params, json=json_body, headers=headers, timeout=30)

    first = request(base_url, method, path, email, token, params=params, json_body=json_body, auth_mode="bearer")
    if first.status_code in (401, 403):
        return request(base_url, method, path, email, token, params=params, json_body=json_body, auth_mode="basic")
    return first


def get_latest_report_dir() -> Path:
    candidates = [p for p in REPORT_DIR.iterdir() if p.is_dir()]
    if not candidates:
        raise RuntimeError("No report directory found")
    return sorted(candidates)[-1]


def build_section(report_dir: Path) -> tuple[str, str, str]:
    source = report_dir.name
    title = f"懂车帝充电日报 {source}"

    prebuilt_html = report_dir / "confluence_section.html"
    summary_md = report_dir / "summary.md"

    if prebuilt_html.exists():
        body = prebuilt_html.read_text(encoding="utf-8")
        markdown = summary_md.read_text(encoding="utf-8") if summary_md.exists() else f"# {title}\n"
        return body, markdown, title

    rows = json.loads((report_dir / "filtered.json").read_text(encoding="utf-8"))
    headers = [
        "车系ID",
        "车型",
        "价格(万元)",
        "纯电续航里程(km)工信部",
        "纯电续航里程(km)CLTC",
        "电池能量密度(Wh/kg)",
        "高压快充平台",
        "充电时间",
        "充电电量",
        "电池容量(kWh)",
        "电芯品牌",
        "电池类型",
        "缺失状态",
        "数据状态",
    ]
    table_lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        table_lines.append("| " + " | ".join(str(r.get(h, "")).replace("\n", " ").replace("|", "/") for h in headers) + " |")

    html_table = ["<table><thead><tr>"]
    for h in headers:
        html_table.append(f"<th>{h}</th>")
    html_table.append("</tr></thead><tbody>")
    for r in rows:
        html_table.append("<tr>")
        for h in headers:
            html_table.append(f"<td>{str(r.get(h, '')).replace(chr(10), ' ')}</td>")
        html_table.append("</tr>")
    html_table.append("</tbody></table>")

    body = (
        f"<!-- DONGCHEDI_DAILY:{source}:START -->"
        f"<h2>{title}</h2>"
        f"<p>数据源: {report_dir.name}</p>"
        f"<p>筛选规则: 价格&gt;20万 且 纯电车型；缺失字段车型持续跟踪。</p>"
        f"<p>当日总车型: {len(rows)}</p>"
        f"{''.join(html_table)}"
        f"<!-- DONGCHEDI_DAILY:{source}:END -->"
    )
    markdown = "\n".join([f"# {title}", "", *table_lines])
    return body, markdown, title


def find_page(base_url: str, email: str, token: str) -> dict[str, Any]:
    queries = [
        'type = page and text ~ "懂车帝"',
        'type = page and text ~ "充电日报"',
        'type = page and text ~ "dongchedi"',
    ]
    for cql in queries:
        resp = request(base_url, "GET", "/rest/api/search", email, token, params={"cql": cql, "limit": 5})
        resp.raise_for_status()
        data = resp.json()
        if data.get("results"):
            item = data["results"][0]
            content = item.get("content", {}) if isinstance(item.get("content", {}), dict) else {}
            return {"id": str(content.get("id", "")), "title": str(content.get("title", "")), "query": cql}
    raise RuntimeError("No matching Confluence page found")


def create_page(base_url: str, email: str, token: str, *, space_key: str, title: str, body: str, parent_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {"storage": {"value": body, "representation": "storage"}},
    }
    if parent_id:
        payload["ancestors"] = [{"id": parent_id}]

    resp = request(base_url, "POST", "/rest/api/content", email, token, json_body=payload)
    resp.raise_for_status()
    return resp.json()


def update_page(
    base_url: str,
    email: str,
    token: str,
    *,
    page_id: str,
    title: str,
    body: str,
    version: int,
    parent_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": page_id,
        "type": "page",
        "title": title,
        "version": {"number": version + 1},
        "body": {"storage": {"value": body, "representation": "storage"}},
    }
    if parent_id:
        payload["ancestors"] = [{"id": parent_id}]

    resp = request(base_url, "PUT", f"/rest/api/content/{page_id}", email, token, json_body=payload)
    resp.raise_for_status()
    return resp.json()


def get_page(base_url: str, email: str, token: str, page_id: str, *, expand: str = "body.storage,version,title,space,ancestors") -> dict[str, Any]:
    resp = request(base_url, "GET", f"/rest/api/content/{page_id}", email, token, params={"expand": expand})
    resp.raise_for_status()
    return resp.json()


def find_child_page(base_url: str, email: str, token: str, *, parent_page_id: str, title: str) -> dict[str, Any] | None:
    cql = f'ancestor = {parent_page_id} and type = "page" and title = "{title}"'
    resp = request(base_url, "GET", "/rest/api/search", email, token, params={"cql": cql, "limit": 5})
    resp.raise_for_status()
    data = resp.json()
    for item in data.get("results", []):
        content = item.get("content", {}) if isinstance(item.get("content", {}), dict) else {}
        if str(content.get("title", "")).strip() == title:
            return {
                "id": str(content.get("id", "")),
                "title": str(content.get("title", "")),
            }
    return None


def find_space_page(base_url: str, email: str, token: str, *, space_key: str, title: str) -> dict[str, Any] | None:
    resp = request(
        base_url,
        "GET",
        "/rest/api/content",
        email,
        token,
        params={"spaceKey": space_key, "title": title, "expand": "ancestors,title", "limit": 10},
    )
    resp.raise_for_status()
    data = resp.json()
    for item in data.get("results", []):
        if str(item.get("title", "")).strip() == title:
            return {
                "id": str(item.get("id", "")),
                "title": str(item.get("title", "")),
            }
    return None


def main() -> int:
    env = load_env()
    base_url = env["CONFLUENCE_BASE_URL"]
    email = env["CONFLUENCE_EMAIL"]
    token = env["CONFLUENCE_API_TOKEN"]
    page_id = env.get("CONFLUENCE_DAILY_PAGE_ID", "").strip()
    parent_page_id = env.get("CONFLUENCE_DAILY_PARENT_PAGE_ID", "").strip()

    report_dir = get_latest_report_dir()
    section_html, markdown, report_title = build_section(report_dir)

    if parent_page_id:
        parent_page = get_page(base_url, email, token, parent_page_id, expand="title,space,ancestors")
        print(f"Using configured parent page {parent_page_id} {parent_page.get('title', '')}")

        parent_space_key = str(((parent_page.get("space") or {}).get("key")) or "")

        child_page = find_child_page(base_url, email, token, parent_page_id=parent_page_id, title=report_title)
        if child_page:
            page_id = child_page["id"]
            page = get_page(base_url, email, token, page_id)
        elif parent_space_key:
            space_page = find_space_page(base_url, email, token, space_key=parent_space_key, title=report_title)
            if space_page:
                page_id = space_page["id"]
                page = get_page(base_url, email, token, page_id)
            else:
                page = parent_page
                page_id = parent_page_id
        else:
            page = parent_page
            page_id = parent_page_id
    else:
        if page_id:
            page = get_page(base_url, email, token, page_id)
        else:
            page = find_page(base_url, email, token)
            page_id = page["id"]
            print(f"Using page {page_id} {page['title']} from query {page['query']}")

    body = (((page.get("body") or {}).get("storage") or {}).get("value") or "")
    title = str(page.get("title", ""))
    space_key = str(((page.get("space") or {}).get("key")) or "")
    version = int(((page.get("version") or {}).get("number")) or 1)

    run_date = report_dir.name
    start = f"<!-- DONGCHEDI_DAILY:{run_date}:START -->"
    end = f"<!-- DONGCHEDI_DAILY:{run_date}:END -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if pattern.search(body):
        new_body = pattern.sub(section_html, body)
    else:
        new_body = body + section_html

    existing_report_match = title.strip().lower() == report_title.strip().lower()
    if existing_report_match:
        result = update_page(
            base_url,
            email,
            token,
            page_id=page_id,
            title=title,
            body=new_body,
            version=version,
            parent_id=parent_page_id or None,
        )
        final_page_id = str(result.get("id", page_id))
        final_title = str(result.get("title", title))
        final_version = int(((result.get("version") or {}).get("number")) or version + 1)
    else:
        if not space_key:
            raise RuntimeError("Cannot create a new page because parent space key was not found")
        created = create_page(
            base_url,
            email,
            token,
            space_key=space_key,
            title=report_title,
            body=section_html,
            parent_id=parent_page_id or page_id,
        )
        final_page_id = str(created.get("id", ""))
        final_title = str(created.get("title", report_title))
        final_version = int(((created.get("version") or {}).get("number")) or 1)

    print(json.dumps({"status": "ok", "page_id": final_page_id, "title": final_title, "version": final_version, "report_dir": str(report_dir), "preview": markdown[:400]}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

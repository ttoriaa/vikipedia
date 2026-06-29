from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def _load_env_file() -> dict[str, str]:
    data: dict[str, str] = {}
    if not ENV_PATH.exists():
        return data
    for line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip().lstrip("\ufeff")] = value.strip()
    return data


_FILE_ENV = _load_env_file()


def env_get(*keys: str, default: str = "") -> str:
    for key in keys:
        value = os.getenv(key)
        if value is not None and value.strip():
            return value.strip()
        file_value = _FILE_ENV.get(key, "").strip()
        if file_value:
            return file_value
    return default


@dataclass
class ConfluenceConfig:
    instance: str
    base_url: str
    token: str
    email: str
    auth_type: str


def resolve_confluence_config(instance: str, *, strict_instance: bool = False) -> ConfluenceConfig:
    upper = instance.upper()
    if strict_instance:
        base_url = env_get(f"{upper}_CONFLUENCE_BASE_URL").rstrip("/")
        token = env_get(f"{upper}_CONFLUENCE_TOKEN")
        email = env_get(f"{upper}_CONFLUENCE_EMAIL")
        auth_type = env_get(f"{upper}_CONFLUENCE_AUTH_TYPE", default="auto").lower()
    else:
        base_url = env_get(f"{upper}_CONFLUENCE_BASE_URL", "CONFLUENCE_BASE_URL").rstrip("/")
        token = env_get(f"{upper}_CONFLUENCE_TOKEN", "CONFLUENCE_API_TOKEN")
        email = env_get(f"{upper}_CONFLUENCE_EMAIL", "CONFLUENCE_EMAIL")
        auth_type = env_get(f"{upper}_CONFLUENCE_AUTH_TYPE", "CONFLUENCE_AUTH_TYPE", default="auto").lower()

    if not base_url:
        if strict_instance:
            raise RuntimeError(
                f"Missing base URL for instance '{instance}' in strict mode. Set {upper}_CONFLUENCE_BASE_URL in .env"
            )
        raise RuntimeError(
            f"Missing base URL for instance '{instance}'. Set {upper}_CONFLUENCE_BASE_URL or CONFLUENCE_BASE_URL in .env"
        )
    if not token:
        if strict_instance:
            raise RuntimeError(
                f"Missing token for instance '{instance}' in strict mode. Set {upper}_CONFLUENCE_TOKEN in .env"
            )
        raise RuntimeError(
            f"Missing token for instance '{instance}'. Set {upper}_CONFLUENCE_TOKEN or CONFLUENCE_API_TOKEN in .env"
        )
    if auth_type not in {"auto", "basic", "bearer"}:
        raise RuntimeError("Confluence auth type must be one of: auto, basic, bearer")

    return ConfluenceConfig(instance=instance, base_url=base_url, token=token, email=email, auth_type=auth_type)


def extract_page_id(page_ref: str) -> str:
    value = page_ref.strip()
    if not value:
        raise ValueError("page reference must not be empty")
    if value.isdigit():
        return value

    parsed = urlparse(value)
    if parsed.scheme and parsed.netloc:
        query = parse_qs(parsed.query)
        if "pageId" in query and query["pageId"]:
            return query["pageId"][0]
        match = re.search(r"/pages/(\d+)/", parsed.path)
        if match:
            return match.group(1)
        match = re.search(r"/content/(\d+)", parsed.path)
        if match:
            return match.group(1)

    raise ValueError(f"Could not extract Confluence page id from '{page_ref}'")


def strip_storage_html(value: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


class ConfluenceClient:
    def __init__(self, config: ConfluenceConfig) -> None:
        self.config = config

    @classmethod
    def for_instance(cls, instance: str) -> "ConfluenceClient":
        return cls(resolve_confluence_config(instance))

    def describe(self) -> dict[str, str]:
        return {
            "instance": self.config.instance,
            "base_url": self.config.base_url,
            "auth_type": self.config.auth_type,
            "email_configured": "yes" if self.config.email else "no",
        }

    def _request_once(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        auth_mode: str,
    ) -> requests.Response:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        url = self.config.base_url.rstrip("/") + path
        kwargs: dict[str, Any] = {"params": params, "json": json_body, "headers": headers, "timeout": 30}
        if auth_mode == "basic":
            if not self.config.email:
                raise RuntimeError(
                    f"Basic auth for instance '{self.config.instance}' requires {self.config.instance.upper()}_CONFLUENCE_EMAIL or CONFLUENCE_EMAIL"
                )
            kwargs["auth"] = (self.config.email, self.config.token)
        elif auth_mode == "bearer":
            headers["Authorization"] = f"Bearer {self.config.token}"
        else:
            raise ValueError(f"Unsupported auth mode: {auth_mode}")
        return requests.request(method, url, **kwargs)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        auth_type = self.config.auth_type
        if auth_type == "auto":
            first = self._request_once(method, path, params=params, json_body=json_body, auth_mode="bearer")
            if first.status_code in (401, 403) and self.config.email:
                response = self._request_once(method, path, params=params, json_body=json_body, auth_mode="basic")
            else:
                response = first
        else:
            response = self._request_once(method, path, params=params, json_body=json_body, auth_mode=auth_type)

        if response.status_code >= 400:
            try:
                detail: Any = response.json()
            except Exception:
                detail = response.text
            raise RuntimeError(f"Confluence API error {response.status_code}: {detail}")

        if not response.text.strip():
            return {}
        return response.json()

    def get_page(self, page_ref: str, *, expand: str = "body.storage,version,title,space,ancestors,_links") -> dict[str, Any]:
        page_id = extract_page_id(page_ref)
        return self.request("GET", f"/rest/api/content/{page_id}", params={"expand": expand})

    def search_cql(self, cql: str, *, limit: int = 10) -> list[dict[str, Any]]:
        data = self.request("GET", "/rest/api/search", params={"cql": cql, "limit": max(1, min(limit, 100))})
        return list(data.get("results", []))

    def search_keyword(
        self,
        query: str,
        *,
        limit: int = 10,
        space_key: str | None = None,
        ancestor_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses = ['type = "page"', f'text ~ "{query.replace(chr(34), chr(92) + chr(34))}"']
        if space_key:
            clauses.append(f'space = "{space_key}"')
        if ancestor_id:
            clauses.append(f"ancestor = {ancestor_id}")
        return self.search_cql(" and ".join(clauses), limit=limit)

    def list_child_pages(self, page_ref: str, *, limit: int = 100, start: int = 0) -> list[dict[str, Any]]:
        page_id = extract_page_id(page_ref)
        data = self.request(
            "GET",
            f"/rest/api/content/{page_id}/child/page",
            params={"limit": max(1, min(limit, 200)), "start": start, "expand": "version,title,_links"},
        )
        return list(data.get("results", []))

    def walk_page_tree(self, page_ref: str, *, max_depth: int = 1) -> list[dict[str, Any]]:
        root = self.get_page(page_ref, expand="title,version,_links")
        queue: list[tuple[dict[str, Any], int]] = [(root, 0)]
        results: list[dict[str, Any]] = []
        while queue:
            current, depth = queue.pop(0)
            page_id = str(current.get("id", ""))
            results.append({
                "id": page_id,
                "title": str(current.get("title", "")),
                "depth": depth,
                "url": self.page_webui_url(current),
            })
            if depth >= max_depth:
                continue
            for child in self.list_child_pages(page_id):
                queue.append((child, depth + 1))
        return results

    def page_webui_url(self, page: dict[str, Any]) -> str:
        links = page.get("_links", {}) if isinstance(page.get("_links", {}), dict) else {}
        webui = str(links.get("webui", ""))
        if webui.startswith("http"):
            return webui
        if webui:
            return self.config.base_url.rstrip("/") + webui
        return ""

    def find_child_page(self, parent_page_ref: str, title: str) -> dict[str, Any] | None:
        parent_id = extract_page_id(parent_page_ref)
        safe_title = title.replace('"', '\\"')
        results = self.search_cql(f'ancestor = {parent_id} and type = "page" and title = "{safe_title}"', limit=10)
        for item in results:
            content = item.get("content", {}) if isinstance(item.get("content", {}), dict) else {}
            if str(content.get("title", "")).strip() == title.strip():
                return content
        return None

    def create_page(self, *, space_key: str, title: str, body_storage: str, parent_page_ref: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {"storage": {"value": body_storage, "representation": "storage"}},
        }
        if parent_page_ref:
            payload["ancestors"] = [{"id": extract_page_id(parent_page_ref)}]
        return self.request("POST", "/rest/api/content", json_body=payload)

    def update_page(self, page_ref: str, *, title: str | None = None, body_storage: str, version: int | None = None) -> dict[str, Any]:
        current = self.get_page(page_ref) if version is None or title is None else {"id": extract_page_id(page_ref), "title": title, "version": {"number": version}}
        page_id = str(current.get("id", extract_page_id(page_ref)))
        next_title = title or str(current.get("title", ""))
        current_version = version if version is not None else int(((current.get("version") or {}).get("number")) or 1)
        payload = {
            "id": page_id,
            "type": "page",
            "title": next_title,
            "version": {"number": current_version + 1},
            "body": {"storage": {"value": body_storage, "representation": "storage"}},
        }
        return self.request("PUT", f"/rest/api/content/{page_id}", json_body=payload)

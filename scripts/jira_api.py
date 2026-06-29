from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

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


class JiraClient:
    def __init__(self) -> None:
        self.base_url = env_get("JIRA_BASE_URL").rstrip("/")
        self.email = env_get("JIRA_EMAIL")
        self.api_token = env_get("JIRA_API_TOKEN")
        self.auth_type = env_get("JIRA_AUTH_TYPE", default="auto").lower()

        if not self.base_url or not self.api_token:
            raise RuntimeError("Missing Jira credentials. Set JIRA_BASE_URL and JIRA_API_TOKEN in .env")
        if self.auth_type not in {"auto", "basic", "bearer"}:
            raise RuntimeError("JIRA_AUTH_TYPE must be one of: auto, basic, bearer")

    def describe(self) -> dict[str, str]:
        return {
            "base_url": self.base_url,
            "auth_type": self.auth_type,
            "email_configured": "yes" if self.email else "no",
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
        url = f"{self.base_url}{path}"
        headers = {"Accept": "application/json"}
        kwargs: dict[str, Any] = {"params": params, "headers": headers, "timeout": 20}
        if json_body is not None:
            headers["Content-Type"] = "application/json"
            kwargs["json"] = json_body
        if auth_mode == "basic":
            if not self.email:
                raise RuntimeError("Jira basic auth requires JIRA_EMAIL in .env")
            kwargs["auth"] = (self.email, self.api_token)
        elif auth_mode == "bearer":
            headers["Authorization"] = f"Bearer {self.api_token}"
        else:
            raise ValueError(f"Unsupported auth mode: {auth_mode}")
        return requests.request(method=method, url=url, **kwargs)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response: requests.Response | None = None
        modes = [self.auth_type] if self.auth_type != "auto" else ["bearer", "basic"]
        for mode in modes:
            for attempt in range(3):
                response = self._request_once(method, path, params=params, json_body=json_body, auth_mode=mode)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "")
                    try:
                        wait_seconds = int(retry_after)
                    except Exception:
                        wait_seconds = 2 * (attempt + 1)
                    time.sleep(max(1, min(wait_seconds, 15)))
                    continue
                if self.auth_type == "auto" and response.status_code in (401, 403) and mode == "bearer":
                    break
                if response.status_code >= 400:
                    try:
                        detail: Any = response.json()
                    except Exception:
                        detail = response.text
                    raise RuntimeError(f"Jira API error {response.status_code}: {detail}")
                return response.json() if response.text.strip() else {}
        if response is None:
            raise RuntimeError("Jira request failed before receiving any response")
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Jira API error {response.status_code}: {detail}")

    def get_issue(self, issue_key: str, *, fields: str = "summary,description,status,issuetype,assignee,reporter,project,updated,created,labels") -> dict[str, Any]:
        return self.request("GET", f"/rest/api/2/issue/{issue_key}", params={"fields": fields})

    def add_comment(self, issue_key: str, body: str) -> dict[str, Any]:
        return self.request("POST", f"/rest/api/2/issue/{issue_key}/comment", json_body={"body": body})

    def update_issue_fields(self, issue_key: str, fields: dict[str, Any]) -> dict[str, Any]:
        return self.request("PUT", f"/rest/api/2/issue/{issue_key}", json_body={"fields": fields})

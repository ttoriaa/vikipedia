from __future__ import annotations

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("jira-local")


def _config() -> tuple[str, str, str]:
    base_url = os.getenv("JIRA_BASE_URL", "").strip().rstrip("/")
    email = os.getenv("JIRA_EMAIL", "").strip()
    api_token = os.getenv("JIRA_API_TOKEN", "").strip()

    if not base_url or not email or not api_token:
        raise RuntimeError(
            "Missing Jira credentials. Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN in .env"
        )

    return base_url, email, api_token


def _request_once(
    base_url: str,
    email: str,
    api_token: str,
    method: str,
    path: str,
    params: dict[str, Any] | None,
    json_body: dict[str, Any] | None,
    auth_mode: str,
) -> requests.Response:
    url = f"{base_url}{path}"
    headers = {"Accept": "application/json"}
    kwargs: dict[str, Any] = {
        "params": params,
        "headers": headers,
        "timeout": 20,
    }

    if json_body is not None:
        headers["Content-Type"] = "application/json"
        kwargs["json"] = json_body

    if auth_mode == "basic":
        kwargs["auth"] = (email, api_token)
    elif auth_mode == "bearer":
        headers["Authorization"] = f"Bearer {api_token}"
    else:
        raise ValueError(f"Unsupported auth mode: {auth_mode}")

    return requests.request(method=method, url=url, **kwargs)


def _request_with_retry(
    base_url: str,
    email: str,
    api_token: str,
    method: str,
    path: str,
    params: dict[str, Any] | None,
    json_body: dict[str, Any] | None,
    auth_mode: str,
) -> requests.Response:
    response: requests.Response | None = None
    for attempt in range(3):
        response = _request_once(
            base_url=base_url,
            email=email,
            api_token=api_token,
            method=method,
            path=path,
            params=params,
            json_body=json_body,
            auth_mode=auth_mode,
        )
        if response.status_code != 429:
            return response

        retry_after_raw = response.headers.get("Retry-After", "")
        try:
            retry_after = int(retry_after_raw)
        except Exception:
            retry_after = 2 * (attempt + 1)

        time.sleep(max(1, min(retry_after, 15)))

    if response is None:
        raise RuntimeError("Jira request failed before receiving any response")
    return response


def _request(
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_url, email, api_token = _config()
    auth_type = os.getenv("JIRA_AUTH_TYPE", "auto").strip().lower()

    if auth_type == "auto":
        first = _request_with_retry(base_url, email, api_token, method, path, params, json_body, "bearer")
        if first.status_code in (401, 403):
            response = _request_with_retry(base_url, email, api_token, method, path, params, json_body, "basic")
        else:
            response = first
    elif auth_type in {"basic", "bearer"}:
        response = _request_with_retry(base_url, email, api_token, method, path, params, json_body, auth_type)
    else:
        raise RuntimeError("JIRA_AUTH_TYPE must be one of: auto, basic, bearer")

    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Jira API error {response.status_code}: {detail}")

    return response.json()


@mcp.tool
def jira_test_connection() -> dict[str, str]:
    """Validate Jira credentials and return current user profile."""
    data = _request("GET", "/rest/api/2/myself")
    return {
        "baseUrl": _config()[0],
        "status": "ok",
        "account": str(data.get("name", "") or data.get("emailAddress", "") or data.get("displayName", "")),
        "displayName": str(data.get("displayName", "")),
    }


@mcp.tool
def jira_search_issues(jql: str, limit: int = 20) -> list[dict[str, str]]:
    """Search Jira issues by JQL."""
    limit = max(1, min(limit, 100))
    data = _request(
        "POST",
        "/rest/api/2/search",
        json_body={
            "jql": jql,
            "startAt": 0,
            "maxResults": limit,
            "fields": ["summary", "status", "issuetype", "assignee", "updated", "project"],
        },
    )

    rows: list[dict[str, str]] = []
    for issue in data.get("issues", []):
        fields = issue.get("fields", {}) if isinstance(issue.get("fields", {}), dict) else {}
        status = fields.get("status", {}) if isinstance(fields.get("status", {}), dict) else {}
        issue_type = fields.get("issuetype", {}) if isinstance(fields.get("issuetype", {}), dict) else {}
        assignee = fields.get("assignee", {}) if isinstance(fields.get("assignee", {}), dict) else {}
        project = fields.get("project", {}) if isinstance(fields.get("project", {}), dict) else {}

        rows.append(
            {
                "key": str(issue.get("key", "")),
                "summary": str(fields.get("summary", "")),
                "status": str(status.get("name", "")),
                "issueType": str(issue_type.get("name", "")),
                "assignee": str(assignee.get("displayName", "")),
                "project": str(project.get("key", "")),
                "updated": str(fields.get("updated", "")),
            }
        )

    return rows


@mcp.tool
def jira_get_issue(issue_key: str) -> dict[str, str]:
    """Get key details for one Jira issue."""
    data = _request(
        "GET",
        f"/rest/api/2/issue/{issue_key}",
        params={"fields": "summary,description,status,issuetype,assignee,reporter,project,updated,created"},
    )
    fields = data.get("fields", {}) if isinstance(data.get("fields", {}), dict) else {}
    status = fields.get("status", {}) if isinstance(fields.get("status", {}), dict) else {}
    issue_type = fields.get("issuetype", {}) if isinstance(fields.get("issuetype", {}), dict) else {}
    assignee = fields.get("assignee", {}) if isinstance(fields.get("assignee", {}), dict) else {}
    reporter = fields.get("reporter", {}) if isinstance(fields.get("reporter", {}), dict) else {}
    project = fields.get("project", {}) if isinstance(fields.get("project", {}), dict) else {}

    description = fields.get("description", "")
    if not isinstance(description, str):
        description = str(description)

    return {
        "key": str(data.get("key", "")),
        "summary": str(fields.get("summary", "")),
        "status": str(status.get("name", "")),
        "issueType": str(issue_type.get("name", "")),
        "assignee": str(assignee.get("displayName", "")),
        "reporter": str(reporter.get("displayName", "")),
        "project": str(project.get("key", "")),
        "created": str(fields.get("created", "")),
        "updated": str(fields.get("updated", "")),
        "description": description,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")

"""Thin, GET-only Jira Cloud REST v3 client. Shared by discover_fields.py and fetch_jira.py.
Invariant: no write verbs. The only POST is the read-only /search/jql endpoint."""
from __future__ import annotations

import time

import requests
from requests.auth import HTTPBasicAuth

_SEARCH_JQL = "/rest/api/3/search/jql"


class JiraError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class JiraClient:
    def __init__(self, base_url: str, email: str, token: str, *, timeout: int = 30):
        self._base = base_url.rstrip("/")
        self._auth = HTTPBasicAuth(email, token)
        self._headers = {"Accept": "application/json"}
        self._timeout = timeout
        self._session = requests.Session()

    # -- transport --------------------------------------------------------------
    def _request(self, method: str, path: str, *, params=None, json_body=None):
        if method == "POST" and path != _SEARCH_JQL:
            raise JiraError(f"blocked non-read POST to {path}")  # guard: read-only agent
        if method not in {"GET", "POST"}:
            raise JiraError(f"blocked write verb {method}")
        url = f"{self._base}{path}"
        for attempt in range(4):
            r = self._session.request(
                method, url, params=params, json=json_body,
                auth=self._auth, headers=self._headers, timeout=self._timeout,
            )
            if r.status_code == 429 or r.status_code >= 500:
                wait = float(r.headers.get("Retry-After", 2 ** attempt))
                time.sleep(min(wait, 30))
                continue
            if r.status_code == 404:
                raise JiraError("issue not found or not visible to this account", 404)
            if r.status_code in (401, 403):
                raise JiraError("authentication/permission failure", r.status_code)
            if not r.ok:
                raise JiraError(f"Jira {r.status_code}: {r.text[:200]}", r.status_code)
            return r.json()
        raise JiraError("Jira unavailable after retries (429/5xx)", 429)

    def _get(self, path: str, **params):
        return self._request("GET", path, params=params or None)

    # -- endpoints ------------------------------------------------------------
    def myself(self) -> dict:
        return self._get("/rest/api/3/myself")

    def list_fields(self) -> list[dict]:
        return self._get("/rest/api/3/field")

    def get_issue(self, key: str, *, fields: str, expand: str) -> dict:
        return self._get(f"/rest/api/3/issue/{key}", fields=fields, expand=expand)

    def get_comments(self, key: str) -> dict:
        return self._get(f"/rest/api/3/issue/{key}/comment", expand="renderedBody", orderBy="created")

    def get_remote_links(self, key: str) -> list[dict]:
        return self._get(f"/rest/api/3/issue/{key}/remotelink")

    def search_jql(self, jql: str, *, fields: list[str], max_results: int = 50) -> dict:
        return self._request(
            "POST", _SEARCH_JQL,
            json_body={"jql": jql, "fields": fields, "maxResults": max_results},
        )

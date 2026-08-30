"""Pull the raw issue bundle, read-only, with a 24h .tmp cache. SOP: architecture/10-tools.md."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from tools._jira import JiraClient
from tools._util import read_json, write_json

# fields from findings.md section 8 mapping table
FIELDS = [
    "summary", "description", "issuetype", "status", "priority", "labels", "components",
    "fixVersions", "parent", "subtasks", "issuelinks", "attachment", "assignee",
    "reporter", "created", "updated", "environment",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _fresh(path: Path, ttl_hours: int) -> bool:
    return (time.time() - path.stat().st_mtime) < ttl_hours * 3600


def fetch_bundle(
    key: str,
    client: JiraClient,
    *,
    cache_dir: Path,
    ac_field_id: str | None = None,
    refresh: bool = False,
    ttl_hours: int = 24,
) -> dict:
    cache = Path(cache_dir) / f"{key}.json"
    if cache.exists() and not refresh and _fresh(cache, ttl_hours):
        return read_json(cache)

    fields = FIELDS + ([ac_field_id] if ac_field_id else [])
    issue = client.get_issue(
        key, fields=",".join(fields), expand="renderedFields,names,changelog"
    )
    bundle = {
        "key": key,
        "fetched_at": _now_iso(),
        "ac_field_id": ac_field_id,
        "issue": issue,
        "comments": client.get_comments(key),
        "remote_links": client.get_remote_links(key),
        "linked": client.search_jql(
            f'issue in linkedIssues("{key}") OR parent = "{key}"',
            fields=["summary", "issuetype", "status"],
        ),
    }
    write_json(cache, bundle)
    return bundle

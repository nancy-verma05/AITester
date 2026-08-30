"""Resolve the Acceptance Criteria custom field id for the site. SOP: architecture/10-tools.md.
GET /rest/api/3/field only."""
from __future__ import annotations

from tools._jira import JiraClient

_NAMES = {"acceptance criteria", "acceptance criteria (ac)", "ac", "definition of done"}


def discover_ac_field(client: JiraClient) -> str | None:
    matches = [
        f for f in client.list_fields()
        if f.get("custom") and (f.get("name") or "").strip().lower() in _NAMES
    ]
    if not matches:
        return None
    exact = [f for f in matches if (f["name"] or "").strip().lower() == "acceptance criteria"]
    return (exact or matches)[0]["id"]

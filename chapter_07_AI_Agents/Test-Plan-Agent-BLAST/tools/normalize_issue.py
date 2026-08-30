"""RawBundle -> pre-IssueContext: HTML/ADF -> Markdown, AC resolution (description first),
field minimisation. No Jira, no LLM, no paraphrasing. SOP: architecture/10-tools.md."""
from __future__ import annotations

import re

try:
    from markdownify import markdownify as _md
except Exception:  # pragma: no cover
    _md = None

# An "Acceptance Criteria" label on its own line: a heading (## AC), a bold list label
# (- **Acceptance Criteria:**), or plain text. Real Jira stories use all three.
_AC_LABEL = re.compile(
    r"(?im)^[ \t>#*_+-]*\s*"
    r"(?:acceptance\s+criteria(?:\s*\(ac\))?|definition\s+of\s+done|\bac\b)"
    r"\s*:?\s*[*_]*\s*$"
)
# Where the AC block ends: the next bold label line or the next heading.
_NEXT_LABEL = re.compile(r"(?im)^\s*(?:[-*+]\s+)?[*_]{2}[^*_\n]+:[*_]{2}|^\s{0,3}#{1,6}\s+\S")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*\S)\s*$", re.M)


# -- rich text -----------------------------------------------------------------
def html_to_md(html: str | None) -> str:
    if not html or not html.strip():
        return ""
    if _md is None:  # pragma: no cover - markdownify is a hard dep
        return re.sub(r"<[^>]+>", "", html).strip()
    return _md(html, heading_style="ATX", bullets="-").strip()


def adf_to_md(adf) -> str:
    """Fallback when renderedFields HTML is missing. Prefers atlas-doc-parser."""
    if not adf:
        return ""
    try:  # pragma: no cover - optional dependency
        from atlas_doc_parser.model import NodeDoc

        return NodeDoc.from_dict(adf).to_markdown().strip()
    except Exception:
        return _adf_walk(adf).strip()


def _adf_walk(node) -> str:
    t = node.get("type")
    kids = node.get("content", []) or []
    if t == "text":
        return node.get("text", "")
    if t in ("paragraph", "heading"):
        pre = "#" * node.get("attrs", {}).get("level", 0) + " " if t == "heading" else ""
        return pre + "".join(_adf_walk(k) for k in kids) + "\n\n"
    if t in ("bulletList", "orderedList"):
        marker = "- " if t == "bulletList" else "1. "
        return "".join(marker + _adf_walk(k).strip() + "\n" for k in kids) + "\n"
    if t in ("listItem", "doc", "tableCell", "tableHeader"):
        return "".join(_adf_walk(k) for k in kids)
    if t == "hardBreak":
        return "\n"
    if t == "codeBlock":
        return "```\n" + "".join(_adf_walk(k) for k in kids) + "\n```\n\n"
    return "".join(_adf_walk(k) for k in kids)


# -- acceptance criteria ------------------------------------------------------
def _split_items(md: str) -> list[str]:
    items = [m.group(1).strip() for m in _LIST_ITEM.finditer(md)]
    items = [i for i in items if i]
    return items or ([md.strip()] if md.strip() else [])


def _ac_from_description(desc_md: str) -> list[str]:
    m = _AC_LABEL.search(desc_md)
    if not m:
        return []
    tail = desc_md[m.end():]
    stop = _NEXT_LABEL.search(tail)
    block = tail[: stop.start()] if stop else tail
    return _split_items(block)


def _resolve_ac(ac_field_id, fields, rendered, desc_md) -> dict:
    if ac_field_id:
        raw = rendered.get(ac_field_id) or fields.get(ac_field_id)
        text = html_to_md(raw) if isinstance(raw, str) else adf_to_md(raw)
        if text.strip():
            return {"source": "custom_field", "field_id": ac_field_id,
                    "items_md": _split_items(text)}
    from_desc = _ac_from_description(desc_md)
    if from_desc:
        return {"source": "description", "field_id": None, "items_md": from_desc}
    return {"source": "none", "field_id": None, "items_md": []}


# -- links / misc -----------------------------------------------------------
def _norm_links(issuelinks: list) -> list[dict]:
    out = []
    for lk in issuelinks or []:
        if "outwardIssue" in lk:
            rel, other = lk["type"].get("outward", "relates to"), lk["outwardIssue"]
        elif "inwardIssue" in lk:
            rel, other = lk["type"].get("inward", "relates to"), lk["inwardIssue"]
        else:
            continue
        of = other.get("fields", {})
        out.append({
            "type": rel, "key": other.get("key"),
            "summary": of.get("summary"),
            "status": (of.get("status") or {}).get("name"),
        })
    return out


def _changelog_signal(issue: dict, ac_field_id: str | None) -> dict:
    ac_changes, status_flips, last = 0, 0, None
    for h in (issue.get("changelog") or {}).get("histories", []):
        for it in h.get("items", []):
            fid = it.get("fieldId") or it.get("field")
            if fid in ("status", "Status"):
                status_flips += 1
            if ac_field_id and fid == ac_field_id:
                ac_changes += 1
                last = h.get("created")
    return {"ac_changed_count": ac_changes, "last_ac_change": last,
            "status_flip_count": status_flips}


def _names(items) -> list[str]:
    return [i.get("name") for i in (items or []) if i.get("name")]


# -- main -------------------------------------------------------------------
def normalize(bundle: dict) -> dict:
    issue = bundle["issue"]
    key = bundle["key"]
    f = issue.get("fields", {}) or {}
    rf = issue.get("renderedFields", {}) or {}
    ac_field_id = bundle.get("ac_field_id")

    desc_md = html_to_md(rf.get("description")) or adf_to_md(f.get("description"))
    env_md = html_to_md(rf.get("environment")) or adf_to_md(f.get("environment")) or None

    comments = []
    for c in (bundle.get("comments") or {}).get("comments", []):
        comments.append({
            "author": (c.get("author") or {}).get("displayName", "Unknown"),
            "created": c.get("created"),
            "body_md": html_to_md(c.get("renderedBody")) or adf_to_md(c.get("body")),
            "trust": "untrusted",
        })

    parent = None
    if f.get("parent"):
        pf = f["parent"].get("fields", {})
        parent = {"key": f["parent"].get("key"), "summary": pf.get("summary"),
                  "type": (pf.get("issuetype") or {}).get("name")}

    base_url = (bundle.get("issue", {}).get("self", "") or "").split("/rest/")[0]

    return {
        "key": key,
        "url": f"{base_url}/browse/{key}" if base_url else f"/browse/{key}",
        "fetched_at": bundle["fetched_at"],
        "issue_type": (f.get("issuetype") or {}).get("name", "Unknown"),
        "status": (f.get("status") or {}).get("name"),
        "priority": (f.get("priority") or {}).get("name"),
        "summary": f.get("summary", ""),
        "description_md": desc_md,
        "acceptance_criteria": _resolve_ac(ac_field_id, f, rf, desc_md),
        "labels": list(f.get("labels") or []),
        "components": _names(f.get("components")),
        "fix_versions": _names(f.get("fixVersions")),
        "environment_md": env_md,
        "comments": comments,
        "links": _norm_links(f.get("issuelinks")),
        "remote_links": [
            {"title": (rl.get("object") or {}).get("title", ""),
             "url": (rl.get("object") or {}).get("url", "")}
            for rl in bundle.get("remote_links", []) if (rl.get("object") or {}).get("url")
        ],
        "attachments": [
            {"filename": a.get("filename", ""), "mime": a.get("mimeType", ""),
             "size": a.get("size")}
            for a in (f.get("attachment") or [])
        ],
        "parent": parent,
        "subtasks": [
            {"key": s.get("key"), "summary": s.get("fields", {}).get("summary"),
             "status": (s.get("fields", {}).get("status") or {}).get("name")}
            for s in (f.get("subtasks") or [])
        ],
        "changelog_signal": _changelog_signal(issue, ac_field_id),
    }

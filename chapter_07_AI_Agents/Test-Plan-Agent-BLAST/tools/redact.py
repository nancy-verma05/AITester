"""Strip secrets / PII from a pre-IssueContext BEFORE it reaches the model (rule B9, Q9).
Records what was removed. SOP: architecture/10-tools.md."""
from __future__ import annotations

import re

from tools._util import estimate_tokens

_PLACEHOLDER = {
    "token": "«redacted:token»",
    "email": "«redacted:email»",
    "pii": "«redacted:pii»",
}

# (kind, pattern). url-credential is handled specially (keeps the scheme).
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("token", re.compile(
        r"(?i)\b(?:xox[baprs]-[\w-]{10,}|sk-[A-Za-z0-9]{20,}|gsk_[A-Za-z0-9]{20,}"
        r"|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,})\b")),
    ("token", re.compile(r"(?i)authorization:\s*(?:bearer|basic)\s+\S+")),
    ("token", re.compile(r"\b[A-Za-z0-9+/]{60,}={0,2}\b")),   # long base64 blobs
    ("url-credential", re.compile(r"(https?://)[^/\s:@]+:[^/\s@]+@")),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
]

_PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("pii", re.compile(r"(?i)\b(?:assigned to|owner|contact|reporter)\s*[:=]?\s*[A-Z][a-z]+ [A-Z][a-z]+")),
    ("pii", re.compile(r"\+?\d[\d\s().-]{8,}\d")),            # phone-ish
]

_TEXT_KEYS = {"description_md", "environment_md", "body_md", "summary"}


class RedactError(RuntimeError):
    pass


def _scrub(s: str, patterns, counts: dict[str, int]) -> str:
    for kind, rx in patterns:
        if kind == "url-credential":
            def _repl(m):
                counts["url-credential"] = counts.get("url-credential", 0) + 1
                return m.group(1) + "«redacted»@"
        else:
            def _repl(m, kind=kind):
                counts[kind] = counts.get(kind, 0) + 1
                return _PLACEHOLDER[kind]
        s = rx.sub(_repl, s)
    return s


def _walk(obj, patterns, counts, *, in_text: bool):
    if isinstance(obj, str):
        return _scrub(obj, patterns, counts) if in_text else obj
    if isinstance(obj, list):
        return [_walk(v, patterns, counts, in_text=in_text) for v in obj]
    if isinstance(obj, dict):
        return {
            k: _walk(v, patterns, counts,
                     in_text=(in_text or k in _TEXT_KEYS or k.endswith("_md")))
            for k, v in obj.items()
        }
    return obj


def redact(pre_context: dict, *, data_policy: str = "standard") -> dict:
    if data_policy == "zdr":
        raise RedactError(
            "DATA_POLICY=zdr requested, but Groq has no zero-retention endpoint configured. "
            "Configure a compliant provider/endpoint before running with zdr."
        )
    patterns = list(_PATTERNS) + (_PII_PATTERNS if data_policy == "redacted" else [])

    counts: dict[str, int] = {}
    ctx = _walk(pre_context, patterns, counts, in_text=False)

    ac = ctx.setdefault("acceptance_criteria", {"source": "none", "field_id": None, "items_md": []})
    ac["items_md"] = [
        it if it.strip() else "«redacted:token» (AC content removed by redaction)"
        for it in ac.get("items_md", [])
    ]

    ctx["redactions"] = [{"kind": k, "count": v} for k, v in sorted(counts.items()) if v]
    ctx["token_estimate"] = estimate_tokens(ctx)
    return ctx

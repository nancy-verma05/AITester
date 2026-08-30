"""Shared helpers: paths, JSON IO, schema/prompt loading, token estimate, fuzzy match.
No secrets, no network, no LLM."""
from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
TMP_DIR = PROJECT_ROOT / ".tmp"
OUT_DIR = PROJECT_ROOT / "out"

# repo-wide test-plan template (render target — used "as-is", Q5)
TEMPLATE_PATH = (
    PROJECT_ROOT.parent.parent
    / "Chapter_02" / "stlc" / "01-test-planning" / "references" / "test-plan-template.md"
)

KEY_RE = re.compile(r"^[A-Z][A-Z0-9]+-[0-9]+$")


class InputError(ValueError):
    """Bad agent input (e.g. malformed issue key)."""


def validate_key(key: str) -> str:
    if not isinstance(key, str) or not KEY_RE.match(key):
        raise InputError(f"Not a valid Jira issue key: {key!r} (expected e.g. PROJ-1234)")
    return key


def read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, obj, *, sort_keys: bool = True) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(obj, indent=2, sort_keys=sort_keys, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return p


def load_schema(name: str) -> dict:
    return read_json(SCHEMAS_DIR / name)


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def estimate_tokens(obj) -> int:
    """Cheap, deterministic proxy: ~4 chars/token on serialised JSON/text."""
    text = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    return (len(text) + 3) // 4


_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall((text or "").lower()))


_STOP = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "to", "of", "in",
    "on", "for", "and", "or", "but", "with", "as", "at", "by", "it", "its", "this", "that",
    "these", "those", "i", "we", "you", "they", "he", "she", "can", "will", "shall",
    "should", "must", "may", "via", "then", "than", "when", "while", "so",
}


def fuzzy_contains(needle: str, haystack: str, *, threshold: float = 0.5) -> bool:
    """True if most of `needle`'s content words (stopwords removed) also occur in `haystack`.
    Deliberately loose: catches gross fabrication (new systems/entities), not numeric drift
    or paraphrase — that is what the HUMAN REVIEW GATE is for. Used by validate_plan check 4."""
    n = _tokens(needle) - _STOP
    if not n:
        return True
    h = _tokens(haystack) - _STOP
    return len(n & h) / len(n) >= threshold

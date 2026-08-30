"""Settings + secret-safe logging. Only navigation/cli build a full Settings; individual
tools take what they need as explicit params so they stay pure and testable."""
from __future__ import annotations

import os
from dataclasses import dataclass

try:  # optional convenience
    from dotenv import load_dotenv

    load_dotenv(override=False)
except Exception:  # pragma: no cover
    pass


class ConfigError(RuntimeError):
    pass


def _req(name: str) -> str:
    v = (os.environ.get(name) or "").strip()
    if not v:
        raise ConfigError(f"Missing required environment variable: {name}")
    return v


@dataclass(frozen=True)
class Settings:
    jira_base_url: str
    jira_email: str
    jira_api_token: str
    jira_ac_field_id: str | None
    groq_api_key: str
    model: str
    model_small: str
    reasoning_effort: str
    max_completion_tokens: int
    data_policy: str
    model_input_limit: int
    seed: int
    http_timeout: int
    raw_cache_ttl_hours: int

    @property
    def secrets(self) -> tuple[str, ...]:
        return tuple(s for s in (self.jira_api_token, self.groq_api_key) if s)


def load_settings() -> Settings:
    dp = (os.environ.get("DATA_POLICY") or "standard").strip().lower()
    if dp not in {"standard", "redacted", "zdr"}:
        raise ConfigError(f"DATA_POLICY must be standard|redacted|zdr, got {dp!r}")
    effort = (os.environ.get("REASONING_EFFORT") or "medium").strip().lower()
    if effort not in {"low", "medium", "high"}:
        raise ConfigError(f"REASONING_EFFORT must be low|medium|high, got {effort!r}")
    return Settings(
        jira_base_url=_req("JIRA_BASE_URL").rstrip("/"),
        jira_email=_req("JIRA_EMAIL"),
        jira_api_token=_req("JIRA_API_TOKEN"),
        jira_ac_field_id=(os.environ.get("JIRA_AC_FIELD_ID") or "").strip() or None,
        groq_api_key=_req("GROQ_API_KEY"),
        model=(os.environ.get("MODEL") or "openai/gpt-oss-120b").strip(),
        model_small=(os.environ.get("MODEL_SMALL") or "openai/gpt-oss-20b").strip(),
        reasoning_effort=effort,
        max_completion_tokens=int(os.environ.get("MAX_COMPLETION_TOKENS") or "8000"),
        data_policy=dp,
        model_input_limit=int(os.environ.get("MODEL_INPUT_LIMIT") or "40000"),
        seed=int(os.environ.get("SEED") or "7"),
        http_timeout=int(os.environ.get("HTTP_TIMEOUT") or "30"),
        raw_cache_ttl_hours=int(os.environ.get("RAW_CACHE_TTL_HOURS") or "24"),
    )


def scrub(text: str, secrets: tuple[str, ...] = ()) -> str:
    """Remove known secrets from a string before logging / surfacing in errors."""
    out = str(text)
    for s in secrets:
        if s:
            out = out.replace(s, "«redacted»")
    return out

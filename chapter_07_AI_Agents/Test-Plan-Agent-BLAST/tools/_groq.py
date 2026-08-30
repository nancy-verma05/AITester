"""Thin Groq client (OpenAI-compatible). Shared by generate_test_plan / repair_plan / budget.
Deterministic wrapper: temperature 0, fixed seed, structured output, strict->json_object
fallback. See findings.md section 11 and LLM.md sections 6-7."""
from __future__ import annotations

import json
import re
import time

import requests

_BASE = "https://api.groq.com/openai/v1"
_DUR_RE = re.compile(r"(?:try again in|in)\s+([\d.]+)\s*s", re.I)
_HDR_RE = re.compile(r"(?:([\d.]+)m)?([\d.]+)s")


def _reset_seconds(headers, body_text: str) -> float:
    ra = headers.get("retry-after")
    if ra:
        try:
            return float(ra)
        except ValueError:
            pass
    m = _DUR_RE.search(body_text or "")
    if m:
        return float(m.group(1))
    h = headers.get("x-ratelimit-reset-tokens") or ""
    hm = _HDR_RE.fullmatch(h.strip())
    if hm:
        return float(hm.group(1) or 0) * 60 + float(hm.group(2))
    return 30.0


class GroqError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class GroqClient:
    def __init__(self, api_key: str, *, timeout: int = 90):
        if not api_key:
            raise GroqError("missing GROQ_API_KEY")
        self._key = api_key
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {api_key}"})

    def list_models(self) -> list[dict]:
        r = self._session.get(f"{_BASE}/models", timeout=self._timeout)
        if not r.ok:
            raise GroqError(f"Groq /models {r.status_code}", r.status_code)
        return r.json().get("data", [])

    def _post_chat(self, payload: dict) -> dict:
        spent = 0.0
        for attempt in range(5):
            r = self._session.post(
                f"{_BASE}/chat/completions", json=payload, timeout=self._timeout
            )
            body = r.text
            is_rate = r.status_code in (429, 413) and "rate_limit" in body.lower()
            if is_rate or r.status_code >= 500:
                wait = _reset_seconds(r.headers, body) if is_rate else 2 ** attempt
                wait = min(wait + 0.5, 65.0)
                if spent + wait > 130:
                    raise GroqError(
                        f"Groq rate limit not clearing (waited {spent:.0f}s). Free tier is "
                        f"8000 tokens/min - lower MAX_COMPLETION_TOKENS / REASONING_EFFORT or "
                        f"upgrade at console.groq.com/settings/billing. Detail: {body[:200]}",
                        r.status_code,
                    )
                time.sleep(wait)
                spent += wait
                continue
            if not r.ok:
                raise GroqError(f"Groq {r.status_code}: {body[:300]}", r.status_code)
            return r.json()
        raise GroqError("Groq unavailable after retries", 429)

    @staticmethod
    def _content(resp: dict) -> str:
        try:
            return resp["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):  # pragma: no cover
            raise GroqError("unexpected Groq response shape")

    def chat_json(
        self,
        *,
        system: str,
        users: list[str],
        schema: dict,
        schema_name: str,
        model: str,
        reasoning_effort: str,
        seed: int,
        max_completion_tokens: int = 8000,
    ) -> tuple[dict, dict, str]:
        """Returns (parsed_json, usage, mode). mode is 'json_schema' or 'json_object'."""
        base = {
            "model": model,
            "temperature": 0,
            "top_p": 1,
            "seed": seed,
            "max_completion_tokens": max_completion_tokens,
            "reasoning_effort": reasoning_effort,
            "include_reasoning": False,
        }
        msgs = [{"role": "system", "content": system}] + [
            {"role": "user", "content": u} for u in users
        ]

        # attempt 1 — strict structured outputs
        try:
            resp = self._post_chat({
                **base,
                "messages": msgs,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": schema_name, "strict": True, "schema": schema},
                },
            })
            return json.loads(self._content(resp)), resp.get("usage", {}), "json_schema"
        except (GroqError, json.JSONDecodeError):
            pass

        # attempt 2 — JSON object mode with the schema pasted into the system message
        fallback_system = (
            system
            + "\n\nReturn ONLY a JSON object that validates against this JSON Schema:\n"
            + json.dumps(schema)
        )
        resp = self._post_chat({
            **base,
            "messages": [{"role": "system", "content": fallback_system}]
            + [{"role": "user", "content": u} for u in users],
            "response_format": {"type": "json_object"},
        })
        content = self._content(resp)
        try:
            return json.loads(content), resp.get("usage", {}), "json_object"
        except json.JSONDecodeError as e:
            raise GroqError(f"model did not return valid JSON: {e}")


def cached_tokens(usage: dict) -> int:
    return int((usage or {}).get("prompt_tokens_details", {}).get("cached_tokens", 0) or 0)

"""LLM call #2 (Groq) - ONLY when validate_plan fails. Fix exactly the listed errors.
SOP: architecture/10-tools.md; prompts/repair.md."""
from __future__ import annotations

import json

from tools._groq import GroqClient
from tools._util import load_prompt, load_schema
from tools.generate_test_plan import _system

_GROQ_SCHEMA = "plan_model.groq.schema.json"


def repair(
    bad_plan: dict,
    errors: list[dict],
    groq: GroqClient,
    *,
    model: str,
    seed: int,
    reasoning_effort: str = "medium",
    max_completion_tokens: int = 8000,
) -> tuple[dict, dict]:
    user = (
        load_prompt("repair.md")
        + json.dumps(errors, indent=2)
        + "\n\n## PlanModel to fix\n```json\n"
        + json.dumps(bad_plan, sort_keys=True, ensure_ascii=False)
        + "\n```\n"
    )
    plan, usage, mode = groq.chat_json(
        system=_system(),
        users=[user],
        schema=load_schema(_GROQ_SCHEMA),
        schema_name="plan_model",
        model=model,
        reasoning_effort=reasoning_effort,
        seed=seed,
        max_completion_tokens=max_completion_tokens,
    )
    plan["meta"] = {
        "key": bad_plan.get("meta", {}).get("key"),
        "status": "DRAFT",
        "model": model,
    }
    return plan, {**(usage or {}), "response_mode": mode}

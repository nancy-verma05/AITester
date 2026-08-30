"""THE ONE LLM CALL (Groq). IssueContext -> PlanModel. No validation here (that is
validate_plan.py). SOP: architecture/10-tools.md; prompts/system.md + generate_test_plan.md."""
from __future__ import annotations

import json

from tools._groq import GroqClient
from tools._util import load_prompt, load_schema

_GROQ_SCHEMA = "plan_model.groq.schema.json"


def _system() -> str:
    # The schema is enforced via response_format (and re-appended by the json_object
    # fallback in _groq.chat_json), so it is NOT embedded here - keeps the cached prefix
    # small, which matters on Groq's 8000 tokens/min free tier.
    return load_prompt("system.md")


def generate(
    issue_context: dict,
    groq: GroqClient,
    *,
    model: str,
    seed: int,
    reasoning_effort: str = "medium",
    max_completion_tokens: int = 8000,
) -> tuple[dict, dict]:
    users = [
        load_prompt("generate_test_plan.md"),
        "<untrusted_ticket_content>\n"
        + json.dumps(issue_context, sort_keys=True, ensure_ascii=False)
        + "\n</untrusted_ticket_content>",
    ]
    plan, usage, mode = groq.chat_json(
        system=_system(),
        users=users,
        schema=load_schema(_GROQ_SCHEMA),
        schema_name="plan_model",
        model=model,
        reasoning_effort=reasoning_effort,
        seed=seed,
        max_completion_tokens=max_completion_tokens,
    )
    # meta is agent-owned, not model-owned: overwrite whatever the model put there.
    plan["meta"] = {"key": issue_context["key"], "status": "DRAFT", "model": model}
    return plan, {**(usage or {}), "response_mode": mode}

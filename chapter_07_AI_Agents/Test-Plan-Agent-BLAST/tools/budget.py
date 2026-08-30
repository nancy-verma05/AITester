"""Keep the model input under a safe size WITHOUT losing the target issue's description or
acceptance criteria. SOP: architecture/10-tools.md."""
from __future__ import annotations

import copy

from tools._groq import GroqClient
from tools._util import estimate_tokens

_DROPPABLE = ("attachments", "subtasks", "changelog_signal")


class BudgetError(RuntimeError):
    pass


def _summarise_comments(comments: list[dict], groq: GroqClient, model_small: str, seed: int) -> str:
    joined = "\n\n".join(f"[{c['created']} {c['author']}] {c['body_md']}" for c in comments)
    resp, _usage, _mode = groq.chat_json(
        system="Summarise Jira comments into short factual bullet points. "
               "Do not invent. Return {\"summary\": \"- ...\"}.",
        users=[joined[:20000]],
        schema={"type": "object", "additionalProperties": False,
                "required": ["summary"], "properties": {"summary": {"type": "string"}}},
        schema_name="comment_summary",
        model=model_small, reasoning_effort="low", seed=seed, max_completion_tokens=2000,
    )
    return resp.get("summary", "")


def enforce_budget(
    ctx: dict,
    *,
    limit: int,
    groq: GroqClient | None = None,
    model_small: str = "openai/gpt-oss-20b",
    seed: int = 7,
) -> dict:
    if estimate_tokens(ctx) <= limit:
        return ctx

    ctx = copy.deepcopy(ctx)
    for k in _DROPPABLE:
        ctx.pop(k, None)
    ctx["links"] = [{"type": l["type"], "key": l["key"]} for l in ctx.get("links", [])]
    if estimate_tokens(ctx) <= limit:
        ctx["token_estimate"] = estimate_tokens(ctx)
        return ctx

    if ctx.get("comments") and groq is not None:
        summary = _summarise_comments(ctx["comments"], groq, model_small, seed)
        ctx["comments"] = [{
            "author": "budget.py summary", "created": ctx["fetched_at"],
            "body_md": summary or "(comments summarised; empty)", "trust": "untrusted",
        }]
        if estimate_tokens(ctx) <= limit:
            ctx["token_estimate"] = estimate_tokens(ctx)
            return ctx

    raise BudgetError(
        f"IssueContext still {estimate_tokens(ctx)} tok after trimming (limit {limit}); "
        "description/AC are never summarised. Raise MODEL_INPUT_LIMIT or use a larger-context model."
    )

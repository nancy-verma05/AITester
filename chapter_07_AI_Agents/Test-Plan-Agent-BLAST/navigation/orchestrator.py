"""SOP 00 - Navigation Flow. run(agent_input, settings) -> AgentOutput dict.
Every branch in architecture/00-navigation-flow.md is here; the tools stay pure."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from tools import budget as budget_tool
from tools import discover_fields as discover_tool
from tools import fetch_jira as fetch_tool
from tools import generate_test_plan as gen_tool
from tools import normalize_issue as norm_tool
from tools import redact as redact_tool
from tools import repair_plan as repair_tool
from tools import render_plan as render_tool
from tools import validate_plan as validate_tool
from tools._config import Settings, scrub
from tools._groq import GroqClient, cached_tokens
from tools._jira import JiraClient, JiraError
from tools._util import OUT_DIR, TMP_DIR, InputError, validate_key, write_json

_SCENARIO_ERR = {"maps_to", "traceability", "assumption_gate"}
_TS_RE = re.compile(r"\b(TS-\d+)\b")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stub_md(key: str, reason: str) -> str:
    return (f"# Test Plan — {key}\n\n"
            f"**Status:** DRAFT — could not be generated.\n\n"
            f"The agent could not fetch this issue: {reason}\n")


def _out(status, key, *, md=None, plan=None, raw=None, summary=None, errors=None) -> dict:
    return {
        "status": status,
        "issue_key": key,
        "artifacts": {
            "test_plan_md": str(OUT_DIR / f"test-plan-{key}.md") if md is not None else "",
            "plan_model_json": str(OUT_DIR / f"test-plan-{key}.json") if plan is not None else None,
            "raw_audit_json": str(OUT_DIR / "raw" / f"{key}.json") if raw else None,
        },
        "summary": summary or {"gaps": 0, "p0": 0, "p1": 0, "p2": 0, "open_questions": 0,
                               "ac_source": "none", "llm_calls": 0, "redactions": 0},
        "errors": errors or [],
    }


def run(agent_input: dict, settings: Settings) -> dict:
    secrets = settings.secrets
    key = validate_key(agent_input["issue_key"])            # step 1
    refresh = bool(agent_input.get("refresh", False))
    ac_override = agent_input.get("ac_field_id") or settings.jira_ac_field_id

    jira = JiraClient(settings.jira_base_url, settings.jira_email, settings.jira_api_token,
                      timeout=settings.http_timeout)
    groq = GroqClient(settings.groq_api_key, timeout=max(settings.http_timeout, 90))
    errors: list[dict] = []

    # step 2 - discover AC field
    ac_field_id = ac_override
    if not ac_field_id:
        try:
            ac_field_id = discover_tool.discover_ac_field(jira)
        except JiraError as e:
            errors.append({"stage": "discover_fields", "message": scrub(str(e), secrets)})

    # step 3 - fetch
    try:
        bundle = fetch_tool.fetch_bundle(
            key, jira, cache_dir=TMP_DIR / "raw", ac_field_id=ac_field_id,
            refresh=refresh, ttl_hours=settings.raw_cache_ttl_hours,
        )
    except JiraError as e:
        reason = scrub(str(e), secrets)
        write_json(OUT_DIR / "raw" / f"{key}.json", {"error": reason})
        (OUT_DIR / f"test-plan-{key}.md").write_text(_stub_md(key, reason), encoding="utf-8")
        return _out("fetch_failed", key, md=True, raw=True,
                    errors=[*errors, {"stage": "fetch_jira", "message": reason}])

    write_json(OUT_DIR / "raw" / f"{key}.json", bundle)          # audit copy

    # steps 4-6 - normalize / redact / budget
    try:
        pre = norm_tool.normalize(bundle)
        ctx = redact_tool.redact(pre, data_policy=settings.data_policy)
        ctx = budget_tool.enforce_budget(
            ctx, limit=settings.model_input_limit, groq=groq,
            model_small=settings.model_small, seed=settings.seed,
        )
    except Exception as e:  # RedactError / BudgetError / normalisation bug
        reason = scrub(f"{type(e).__name__}: {e}", secrets)
        (OUT_DIR / f"test-plan-{key}.md").write_text(_stub_md(key, reason), encoding="utf-8")
        return _out("fetch_failed", key, md=True, raw=True,
                    errors=[*errors, {"stage": "normalize_issue", "message": reason}])
    write_json(TMP_DIR / "context" / f"{key}.json", ctx)
    ac_source = ctx["acceptance_criteria"]["source"]

    # step 7 - the one LLM call
    llm_calls = 0
    try:
        plan, usage = gen_tool.generate(
            ctx, groq, model=settings.model, seed=settings.seed,
            reasoning_effort=settings.reasoning_effort,
            max_completion_tokens=settings.max_completion_tokens,
        )
        llm_calls += 1
    except Exception as e:
        reason = scrub(f"{type(e).__name__}: {e}", secrets)
        (OUT_DIR / f"test-plan-{key}.md").write_text(_stub_md(key, reason), encoding="utf-8")
        return _out("fetch_failed", key, md=True, raw=True,
                    errors=[*errors, {"stage": "generate_test_plan", "message": reason}])
    write_json(TMP_DIR / "plan" / f"{key}.json", plan)

    # steps 8-9 - validate, repair once
    result = validate_tool.validate(plan, ctx)
    status = "ok"
    if not result["ok"]:
        try:
            plan, rusage = repair_tool.repair(
                plan, result["errors"], groq, model=settings.model, seed=settings.seed,
                reasoning_effort=settings.reasoning_effort,
                max_completion_tokens=settings.max_completion_tokens,
            )
            llm_calls += 1
            usage = {**usage, "repair": rusage}
        except Exception as e:
            errors.append({"stage": "repair_plan", "message": scrub(str(e), secrets)})
        result = validate_tool.validate(plan, ctx)

    if not result["ok"]:
        status = "validation_failed"
        schema_broken = any(e["code"] == "schema" for e in result["errors"])
        if not schema_broken:
            bad_ids = {m for e in result["errors"] if e["code"] in _SCENARIO_ERR
                       for m in _TS_RE.findall(e["detail"])}
            if bad_ids:
                plan["scenarios"] = [s for s in plan["scenarios"] if s["id"] not in bad_ids]
                plan["human_review_gate"]["open_questions"].append(
                    "Scenarios " + ", ".join(sorted(bad_ids)) +
                    " were removed by the agent because they failed traceability/mapping "
                    "validation. A human must recreate or discard them."
                )
        for e in result["errors"]:
            errors.append({"stage": "validate_plan", "message": f"{e['code']}: {e['detail']}"})

    # step 10 - render
    write_json(TMP_DIR / "plan" / f"{key}.json", plan)
    schema_broken = any(e["code"] == "schema" for e in result["errors"]) if not result["ok"] else False
    if schema_broken:
        md = (_stub_md(key, "the model output did not match the required schema even after repair")
              + "\nThe raw generation is saved as JSON alongside this file for inspection.\n")
    else:
        md = render_tool.render_markdown(plan, issue_context=ctx, generated_at=_now())
    (OUT_DIR / f"test-plan-{key}.md").write_text(md, encoding="utf-8")
    write_json(OUT_DIR / f"test-plan-{key}.json", plan)

    # step 11 - AgentOutput
    prio = [s["priority"] for s in plan.get("scenarios", [])]
    summary = {
        "gaps": len(plan.get("gaps", [])),
        "p0": prio.count("P0"), "p1": prio.count("P1"), "p2": prio.count("P2"),
        "open_questions": len(plan.get("human_review_gate", {}).get("open_questions", [])),
        "ac_source": ac_source,
        "llm_calls": llm_calls,
        "redactions": sum(r["count"] for r in ctx.get("redactions", [])),
        "cached_tokens": cached_tokens(usage),
        "response_mode": usage.get("response_mode"),
        "warnings": result.get("warnings", []),
    }
    return _out(status, key, md=True, plan=True, raw=True, summary=summary, errors=errors)
